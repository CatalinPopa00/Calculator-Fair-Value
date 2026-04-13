from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cachetools import TTLCache
import uvicorn
import math
import statistics
import datetime
from typing import List, Dict, Any, Optional

import urllib.request
import urllib.parse
import json
import os
import requests
import concurrent.futures

from .scraper.yahoo import get_company_data, get_competitors_data, get_market_averages, search_companies, get_analyst_data, get_risk_free_rate
from .utils.kv import kv_get, kv_set
from .models.valuation import (
    calculate_peter_lynch, 
    calculate_peg_fair_value, 
    calculate_dcf, 
    calculate_relative_valuation,
    calculate_dcf_sensitivity,
    calculate_reverse_dcf
)
from .models.scoring import calculate_scoring_reform, calculate_piotroski_score

# Cache Settings
search_cache = TTLCache(maxsize=500, ttl=30 * 60)
valuation_cache = TTLCache(maxsize=1000, ttl=60 * 60)
CACHE_VERSION = "v164"

app = FastAPI(title="Fair Value Calculator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WATCHLIST_FILE = "watchlist.json"
OVERRIDES_FILE = "overrides.json"

class WatchlistRequest(BaseModel):
    tickers: list[str]

class OverrideRequest(BaseModel):
    ticker: str
    inputs: dict = {}
    toggles: dict = {}
    computed: dict = {}
    weights: dict = {}

def _load_overrides() -> dict:
    data = kv_get("overrides")
    if data is not None: return data
    if os.path.exists(OVERRIDES_FILE):
        try:
            with open(OVERRIDES_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def _save_overrides(data: dict):
    kv_set("overrides", data)
    try:
        with open(OVERRIDES_FILE, "w") as f: json.dump(data, f)
    except: pass

def get_recommended_exit_multiple(sector: str, industry: str) -> float:
    s = str(sector).lower()
    ind = str(industry).lower()
    if any(x in s for x in ["tech", "soft", "health", "communication"]): return 15.0
    if any(x in s for x in ["defensive", "utilities", "staple"]): return 12.0
    if any(x in s for x in ["energy", "oil", "gas", "material", "industrial", "manufacturing"]) or "auto" in ind: return 8.0
    if any(x in s for x in ["financial", "bank", "insurance", "real estate", "reit"]): return 10.0
    return 10.0

def deep_clean_data(val):
    if isinstance(val, dict): return {k: deep_clean_data(v) for k, v in val.items()}
    if isinstance(val, list): return [deep_clean_data(v) for v in val]
    if hasattr(val, "item"): return val.item()
    if isinstance(val, (int, float, str, bool)) or val is None: return val
    return str(val)

def sanitize(val):
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))): return None
    return round(float(val), 4)

@app.get("/api/search/{query}")
def search(query: str, response: Response):
    if response: response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    q_key = query.lower().strip()
    if q_key in search_cache: return search_cache[q_key]
    result = search_companies(query)
    if result or len(q_key) <= 2: search_cache[q_key] = result
    return result

@app.get("/api/valuation/{ticker}")
def get_valuation(ticker: str, response: Response, wacc: float = None, fast_mode: bool = False, skip_peers: bool = False):
    if response: response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    ticker_upper = ticker.upper()
    
    try:
        norm_wacc = round(float(wacc), 2) if wacc is not None else "def"
        cache_key = f"val_{ticker_upper}_{fast_mode}_{skip_peers}_{CACHE_VERSION}_{norm_wacc}"
        
        if cache_key in valuation_cache: return valuation_cache[cache_key]

        # PHASE 1: Data Acquisition
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            main_task = executor.submit(get_company_data, ticker_upper, fast_mode=fast_mode)
            risk_free_task = executor.submit(get_risk_free_rate)
            market_task = executor.submit(get_market_averages)
            peer_task = None
            if not skip_peers:
                peer_task = executor.submit(get_competitors_data, ticker_upper, None, None, limit=3)
            
            data = main_task.result() or {}
            rf_rate = risk_free_task.result() or 0.042
            market_data = market_task.result() or {"pe": 20.0, "yield": 0.015}
            peers_data = []
            if peer_task:
                try: peers_data = peer_task.result(timeout=8) or []
                except: peers_data = []

        # Ticker Overrides
        all_overrides = _load_overrides()
        ovr = all_overrides.get(ticker_upper)
        if ovr:
            data.update(ovr.get("inputs", {}))
            data.update(ovr.get("computed", {}))

        # PHASE 2: Core Metrics
        current_price = data.get("current_price") or 0.0
        eps_for_valuation = data.get("adjusted_eps") or data.get("trailing_eps") or 0.0
        # Check FY0 projection if TTM is missing
        eps_0y = next((e.get("avg") for e in data.get("eps_estimates", []) if e.get("period_code") == "0y"), None)
        if eps_for_valuation <= 0 and eps_0y: eps_for_valuation = eps_0y
        
        growth_5y = data.get("eps_5yr_growth") or 0.05
        pe_historic = data.get("pe_historic") or 20.0
        
        # Peer stats
        valid_pes = [p.get('pe_ratio') for p in peers_data if p.get('pe_ratio') and p.get('pe_ratio') > 0]
        sector_median_pe = statistics.median(valid_pes) if valid_pes else market_data.get("pe", 20.0)
        
        # PHASE 3: Models
        lynch = calculate_peter_lynch(current_price, eps_for_valuation, growth_5y, pe_historic, sector_median_pe)
        
        current_pe = current_price / eps_for_valuation if eps_for_valuation > 0 else 0
        company_peg = current_pe / (growth_5y * 100) if growth_5y > 0 else 0
        peg_fv = calculate_peg_fair_value(current_price, company_peg, sector_median_pe / 15.0)
        
        fcf = data.get("fcf") or 0
        shares = data.get("shares_outstanding") or 1
        d_rate = (wacc / 100.0) if wacc is not None else (rf_rate + 0.055)
        rec_exit = get_recommended_exit_multiple(data.get("sector"), data.get("industry"))
        
        dcf_res = calculate_dcf(fcf, growth_5y, d_rate, 0.02, shares, data.get("total_cash", 0), data.get("total_debt", 0), exit_multiple=rec_exit)
        relative_fv = calculate_relative_valuation(ticker_upper, {"trailing_eps": eps_for_valuation}, peers_data)

        # PHASE 4: Scoring
        scoring_results = calculate_scoring_reform({"mos": 0, "eps_growth": growth_5y*100, "pe": current_pe, "pe_historic": pe_historic, "peg_ratio": company_peg}, data)
        health_score = scoring_results.get("health_score_total", 0)
        health_breakdown = scoring_results.get("health_breakdown", [])
        buy_score = scoring_results.get("good_to_buy_total", 0)
        buy_breakdown = scoring_results.get("buy_breakdown", [])
        
        try:
            p_res = calculate_piotroski_score(data)
            p_score = p_res.get("score", "N/A")
            p_breakdown = p_res.get("breakdown", [])
        except:
            p_score = "N/A"; p_breakdown = []

        all_b = health_breakdown + buy_breakdown
        top_s = sorted([b for b in all_b if b.get("points_awarded") == b.get("max_points") and b.get("max_points", 0) > 0], key=lambda x: x.get("max_points", 0), reverse=True)[:3]
        top_r = [b for b in all_b if b.get("points_awarded") == 0][:3]

        # PHASE 5: Weighted Fair Value
        fv_val = None
        weights = {"lynch": 0.3, "peg": 0.2, "dcf": 0.3, "relative": 0.2}
        if data.get("sector") == "Financial Services": weights = {"lynch": 0.45, "relative": 0.45, "peg": 0.1, "dcf": 0}
        
        vals = {"lynch": lynch.get("fair_value"), "peg": peg_fv, "dcf": (dcf_res["dcf_perpetual"]["fair_value"] if dcf_res else None), "relative": relative_fv}
        weighted_sum = 0; total_w = 0
        for k, v in vals.items():
            if v and v > 0:
                weighted_sum += v * weights[k]; total_w += weights[k]
        
        fair_value = (weighted_sum / total_w) if total_w > 0 else None
        mos = ((fair_value - current_price) / current_price * 100) if fair_value and current_price > 0 else 0

        # Build Response
        resp_data = {
            "ticker": ticker_upper,
            "name": data.get("name", ticker_upper),
            "price": current_price,
            "fair_value": sanitize(fair_value),
            "margin_of_safety": sanitize(mos),
            "sector": data.get("sector"),
            "industry": data.get("industry"),
            "metrics": data,
            "valuation": {
                "peter_lynch": lynch,
                "peg_fair_value": sanitize(peg_fv),
                "dcf": dcf_res,
                "relative": sanitize(relative_fv)
            },
            "scoring": {
                "health_score": health_score,
                "health_breakdown": health_breakdown,
                "buy_score": buy_score,
                "buy_breakdown": buy_breakdown,
                "piotroski_score": p_score,
                "piotroski_breakdown": p_breakdown
            },
            "insights": {"strengths": top_s, "risks": top_r, "synthesis": data.get("summary_ro")},
            "debug_version": f"{CACHE_VERSION}-RESET-FIX-ACTIVE",
            "historical_anchors": data.get("historical_anchors", []),
            "historical_trends": data.get("historical_trends", []),
            "historical_data": data.get("historical_data", {}),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        valuation_cache[cache_key] = resp_data
        return resp_data

    except Exception as e:
        import traceback
        print(f"CRASH {ticker}: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/watchlist")
def get_watchlist():
    data = kv_get("watchlist") or []
    return list(set([t.upper() for t in data]))

@app.post("/api/watchlist")
def save_watchlist(req: WatchlistRequest):
    kv_set("watchlist", req.tickers)
    return {"status": "success"}

@app.get("/api/overrides")
def get_overrides(): return _load_overrides()

@app.post("/api/overrides")
def save_override(req: OverrideRequest):
    all_ovr = _load_overrides()
    all_ovr[req.ticker.upper()] = {"inputs": req.inputs, "toggles": req.toggles, "computed": req.computed, "weights": req.weights}
    _save_overrides(all_ovr)
    return {"status": "success"}

@app.delete("/api/overrides/{ticker}")
def delete_override(ticker: str):
    all_ovr = _load_overrides()
    if ticker.upper() in all_ovr:
        del all_ovr[ticker.upper()]
        _save_overrides(all_ovr)
    return {"status": "success"}

@app.post("/api/batch-valuation")
def get_batch_valuation(req: WatchlistRequest):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_valuation, t.upper(), None, None, False, False): t for t in req.tickers}
        for f in concurrent.futures.as_completed(futures):
            try:
                res = f.result()
                if res: results.append(res)
            except: pass
    return results

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
