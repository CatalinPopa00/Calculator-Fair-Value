from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cachetools import TTLCache
import uvicorn
import math
import statistics
import datetime
import os
import json
import concurrent.futures
import traceback
from typing import List, Dict, Any, Optional

from .scraper.yahoo import (
    get_company_data, 
    get_competitors_data, 
    get_market_averages, 
    search_companies, 
    get_analyst_data, 
    get_risk_free_rate
)
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
CACHE_VERSION = "v171" 

app = FastAPI(title="Fair Value Calculator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Static Files (Frontend)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/api_static", StaticFiles(directory=ROOT_DIR), name="api_static") # Backup mount
# We'll use a safer approach for the root to avoid shadowing /api/
@app.get("/")
def read_index():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(ROOT_DIR, "index.html"))

# For other static files (app.js, style.css, etc.)
@app.get("/{filename}")
def read_static(filename: str):
    from fastapi.responses import FileResponse
    path = os.path.join(ROOT_DIR, filename)
    if os.path.exists(path) and os.path.isfile(path):
        return FileResponse(path)
    raise HTTPException(status_code=404)


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

def sanitize(val):
    if val is None: return None
    try:
        fval = float(val)
        if math.isnan(fval) or math.isinf(fval): return None
        return round(fval, 4)
    except: return None

def deep_clean_data(val):
    """Recursively santizies data for JSON compliance (handles NaN, Infinity, and non-serializable objects)."""
    if isinstance(val, dict):
        return {k: deep_clean_data(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [deep_clean_data(v) for v in val]
    
    # Handle common primitives first (Speed)
    if val is None: return None
    if isinstance(val, (str, bool)): return val
    
    # Check for basic Python float/int
    if isinstance(val, (float, int)):
        if math.isnan(val) or math.isinf(val): return None
        return val
        
    # Handle scalar objects (like numpy.float64, pandas.NA, etc.)
    # We use duck-typing to detect number-like objects
    if hasattr(val, "item") and callable(val.item): 
        try:
            native = val.item()
            if isinstance(native, float):
                if math.isnan(native) or math.isinf(native): return None
            return native
        except: pass
        
    try:
        # Final catch-all for anything that can be cast to float (like decimal.Decimal)
        # But we must NOT convert strings or complex objects here
        if hasattr(val, "__float__") and not isinstance(val, (str, list, dict)):
            fval = float(val)
            if math.isnan(fval) or math.isinf(fval): return None
            # Return int if it's an exact integer representation
            if fval.is_integer() and isinstance(val, (int, float)): return int(fval)
            return fval
    except: pass
    
    return str(val)



@app.get("/api/search/{query}")
def search(query: str, response: Response):
    if response: response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    q_key = query.lower().strip()
    if q_key in search_cache: return search_cache[q_key]
    result = search_companies(query)
    if result or len(q_key) <= 2: search_cache[q_key] = result
    return result

@app.get("/api/analyst/{ticker}")
def get_analyst(ticker: str, response: Response):
    """Refined analyst data endpoint (v165 fix for 404)"""
    if response: response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    ticker_upper = ticker.upper()
    cache_key = f"analyst_{ticker_upper}_{CACHE_VERSION}"
    if cache_key in valuation_cache: return valuation_cache[cache_key]
    try:
        result = get_analyst_data(ticker_upper)
        valuation_cache[cache_key] = result
        return result
    except Exception as e:
        print(f"Analyst API error for {ticker_upper}: {e}")
        return {"ticker": ticker_upper, "error": str(e)}

@app.get("/api/valuation/{ticker}")
def get_valuation(ticker: str, response: Response, wacc: float = None, fast_mode: bool = False, skip_peers: bool = False):
    if response: response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    ticker_upper = ticker.upper()
    ticker_upper = ticker_upper.replace(".O", "").replace(".OQ", "").replace(".N", "")
    
    try:
        norm_wacc = round(float(wacc), 2) if wacc is not None else "def"
        cache_key = f"val_{ticker_upper}_{fast_mode}_{skip_peers}_{CACHE_VERSION}_{norm_wacc}"
        
        # v177: Temporary cache-bust for validation
        # if cache_key in valuation_cache: 
        #     return deep_clean_data(valuation_cache[cache_key])


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
                try: peers_data = peer_task.result(timeout=10) or []
                except: peers_data = []

        # Ensure minimal data safety
        if not data.get("name"): data["name"] = ticker_upper; data["ticker"] = ticker_upper

        # Ticker Overrides
        all_overrides = _load_overrides()
        ovr = all_overrides.get(ticker_upper)
        if ovr:
            if "inputs" in ovr: data.update(ovr["inputs"])
            if "computed" in ovr: data.update(ovr["computed"])

        # Core Metrics
        current_price = data.get("current_price") or 0.0
        trailing_eps = data.get("trailing_eps") or 0.0
        adjusted_eps = data.get("adjusted_eps") or trailing_eps
        
        eps_estimates = data.get("eps_estimates", [])
        eps_0y = next((e.get("avg") for e in eps_estimates if e.get("period_code") == "0y"), None)
        
        eps_for_valuation = adjusted_eps
        if eps_for_valuation <= 0 and eps_0y: eps_for_valuation = eps_0y
        
        growth_5y = data.get("eps_5yr_growth") or 0.05
        pe_historic = data.get("pe_historic") or 20.0
        
        # Peter Lynch
        valid_pes = [p.get('pe_ratio') for p in peers_data if p.get('pe_ratio') and p.get('pe_ratio') > 0]
        sector_median_pe = statistics.median(valid_pes) if valid_pes else market_data.get("pe", 20.0)
        lynch = calculate_peter_lynch(current_price, eps_for_valuation, growth_5y, pe_historic, sector_median_pe)
        
        # PEG
        current_pe = current_price / eps_for_valuation if eps_for_valuation > 0 else 0
        company_peg = current_pe / (growth_5y * 100) if growth_5y > 0 else 0
        peg_fv = calculate_peg_fair_value(current_price, company_peg, sector_median_pe / 15.0)
        
        # DCF
        fcf = data.get("fcf") or 0
        shares = data.get("shares_outstanding") or 1
        discount_rate = (wacc / 100.0) if wacc is not None else (rf_rate + 0.055)
        rec_exit = get_recommended_exit_multiple(data.get("sector"), data.get("industry"))
        dcf_res = calculate_dcf(fcf, growth_5y, discount_rate, 0.02, shares, data.get("total_cash", 0), data.get("total_debt", 0), exit_multiple=rec_exit)
        
        # Relative
        relative_val = calculate_relative_valuation(ticker_upper, {"trailing_eps": eps_for_valuation}, peers_data)

        # EV / EBITDA calculation (v172: fix for 0.00x)
        ebitda_val = data.get("ebitda")
        if ebitda_val and ebitda_val > 0:
            mkt_cap = (data.get("shares_outstanding") or 0) * current_price
            debt_val = (data.get("total_debt") or 0)
            cash_val = (data.get("total_cash") or 0)
            ev_val = mkt_cap + debt_val - cash_val
            data["ev_to_ebitda"] = ev_val / ebitda_val
        else:
            data["ev_to_ebitda"] = 0

        # ── FCF Trend Calculation (v182: Enhanced for Accuracy) ────────────────
        anchors = data.get("historical_anchors", [])
        # Extract FCF and filter for reported (actual) years
        actual_fcf = [a.get("fcf_b") for a in anchors if a.get("fcf_b") is not None and "(Est)" not in str(a.get("year", ""))]
        
        if len(actual_fcf) >= 2:
            # Anchors are newest first
            actual_fcf_chrono = list(reversed(actual_fcf))
            last_fcf = actual_fcf_chrono[-1]
            # Use average of all previous years as baseline if more than 2, else just the previous one
            prev_avg = sum(actual_fcf_chrono[:-1]) / len(actual_fcf_chrono[:-1])
            
            # v182: Dynamic trend labeling
            if last_fcf > prev_avg * 1.05 and last_fcf > 0:
                data["fcf_trend"] = "Growing"
            elif last_fcf < prev_avg * 0.95:
                data["fcf_trend"] = "Declining"
            else:
                data["fcf_trend"] = "Flat"
        else:
            data["fcf_trend"] = "Flat"
        
        # Add market_data to context for scoring
        data["market_data"] = market_data

        # Scoring
        scoring_results = calculate_scoring_reform({"mos": (lynch.get("margin_of_safety") if lynch else 0), "eps_growth": growth_5y*100, "pe": current_pe, "pe_historic": pe_historic, "peg_ratio": company_peg}, data)

        health_score_total = scoring_results.get("health_score_total")
        health_breakdown = scoring_results.get("health_breakdown")
        good_to_buy_total = scoring_results.get("good_to_buy_total")
        buy_breakdown = scoring_results.get("buy_breakdown")
        
        try:
            p_res = calculate_piotroski_score(data)
            p_score = p_res.get("score")
            p_breakdown = p_res.get("breakdown", [])
        except:
            p_score = "N/A"; p_breakdown = []

        all_breakdowns = (health_breakdown or []) + (buy_breakdown or [])
        top_strengths = sorted([b for b in all_breakdowns if b.get("points_awarded") == b.get("max_points") and b.get("max_points", 0) > 0], key=lambda x: x.get("max_points", 0), reverse=True)[:3]
        risk_factors = [b for b in all_breakdowns if b.get("points_awarded") == 0][:3]

        # Weighted Fair Value
        weights = {"lynch": 0.3, "peg": 0.2, "dcf": 0.3, "relative": 0.2}
        if data.get("sector") == "Financial Services":
            weights = {"lynch": 0.45, "relative": 0.45, "peg": 0.1, "dcf": 0}
        
        vals = {"lynch": lynch.get("fair_value"), "peg": peg_fv, "dcf": (dcf_res["dcf_perpetual"]["fair_value"] if dcf_res else None), "relative": relative_val}
        w_sum = 0; w_total = 0
        for k, v in vals.items():
            if v and v > 0:
                w_sum += v * weights[k]; w_total += weights[k]
        fair_value = (w_sum / w_total) if w_total > 0 else None
        overall_mos = ((fair_value - current_price) / current_price * 100) if fair_value and current_price > 0 else 0

        # Process DCF into the exact structure app.js expects (v166 fix)
        dcf_perp_data = dcf_res.get("dcf_perpetual", {}) if dcf_res else {}
        dcf_exit_data = dcf_res.get("dcf_exit_multiple", {}) if dcf_res else {}
        
        # Sensitivity Matrix (calculate it if missing or just provide the base one)
        sens_matrix = calculate_dcf_sensitivity(fcf, growth_5y, shares, data.get("total_cash", 0), data.get("total_debt", 0), 5, discount_rate, 0.02, rec_exit)

        def map_dcf_obj(obj, is_perp=True):
            if not obj: return None
            return {
                "fair_value_per_share": sanitize(obj.get("fair_value")),
                "terminal_value": sanitize(obj.get("terminal_value")),
                "present_value_terminal": sanitize(obj.get("pv_terminal_value")),
                "present_value_fcf_sum": sanitize(dcf_res.get("total_pv_of_fcfs")),
                "fcf_projections": [sanitize(v) for v in dcf_res.get("fcf_years", [])],
                "discount_rate": sanitize(discount_rate),
                "perpetual_growth_rate": sanitize(0.02) if is_perp else None,
                "exit_multiple": sanitize(rec_exit) if not is_perp else None,
                "sensitivity_matrix": sens_matrix if is_perp else []
            }

        dcf_perp_mapped = map_dcf_obj(dcf_perp_data, True)
        dcf_exit_mapped = map_dcf_obj(dcf_exit_data, False)

        # Build Response (Full app.js Compatibility)
        resp_data = {
            "ticker": ticker_upper,
            "name": data.get("name", ticker_upper),
            "current_price": float(current_price),
            "fair_value": sanitize(fair_value),
            "margin_of_safety": sanitize(overall_mos),
            "dcf_value": sanitize(vals["dcf"]),
            "relative_value": sanitize(vals["relative"]),
            "peg_value": sanitize(vals["peg"]),
            "lynch_fair_value": sanitize(vals["lynch"]),
            "lynch_status": lynch.get("status"),
            "health_score_total": health_score_total,
            "health_breakdown": health_breakdown,
            "good_to_buy_total": good_to_buy_total,
            "buy_breakdown": buy_breakdown,
            "market_data": market_data, # v178: Fix for 'Platform cannot see S&P 500 PE'
            "piotroski_score": p_score,
            "piotroski_breakdown": p_breakdown,
            "dcf_assumptions": {
                "recommended_exit_multiple": rec_exit,
                "wacc": discount_rate * 100,
                "perpetual_growth": 2.0
            },
            "company_profile": {
                "sector": data.get("sector"),
                "industry": data.get("industry"),
                "business_summary": data.get("business_summary"),
                "market_cap": sanitize((data.get("shares_outstanding") or 0) * current_price),
                "trailing_pe": sanitize(current_pe),
                "trailing_eps": sanitize(eps_for_valuation),
                "adjusted_eps": sanitize(adjusted_eps),
                "historic_pe": sanitize(data.get("pe_historic")),
                "debt_to_equity": sanitize(data.get("debt_to_equity")),
                "operating_margin": sanitize(data.get("operating_margin")),
                "revenue_growth": sanitize(data.get("revenue_growth")),
                "earnings_growth": sanitize(growth_5y),
                "next_earnings_date": data.get("next_earnings_date"),
                "sector_median_pe": sanitize(sector_median_pe),
                "insider_ownership": sanitize(data.get("insider_ownership")),
                "shares_outstanding": sanitize(data.get("shares_outstanding")),
                "buyback_rate": sanitize(data.get("historic_buyback_rate")),
                "dividend_yield": sanitize(data.get("dividend_yield")),
                "payout_ratio": sanitize(data.get("payout_ratio")),
                "dividend_streak": data.get("dividend_streak"),
                "dividend_cagr_5y": sanitize(data.get("dividend_cagr_5y")),
                "competitors": [p.get("ticker") for p in peers_data] if peers_data else [],
                "competitor_metrics": peers_data or []
            },
            "metrics": data,
            "valuation": {
                "peter_lynch": lynch,
                "peg_fair_value": sanitize(peg_fv),
                "dcf": {
                    "eps_growth_applied": sanitize(growth_5y),
                    "shares_outstanding": shares,
                    "total_cash": data.get("total_cash", 0),
                    "total_debt": data.get("total_debt", 0),
                    "dcf_perpetual": dcf_perp_mapped,
                    "dcf_exit_multiple": dcf_exit_mapped
                },
                "relative": sanitize(relative_val)
            },
            "scoring": {
                "health_score": health_score_total,
                "buy_score": good_to_buy_total,
                "piotroski_score": p_score
            },
            "algorithmic_insights": {
                "top_strengths": top_strengths,
                "risk_factors": risk_factors
            },
            "formula_data": {
               "peter_lynch": {
                   "fair_value": sanitize(vals["lynch"]), 
                   "fwd_pe": sanitize(lynch.get("fwd_pe")), 
                   "status": lynch.get("status"),
                   "trailing_eps": sanitize(eps_for_valuation),
                   "eps_growth_estimated": sanitize(growth_5y),
                   "historic_pe": sanitize(pe_historic)
               },
               "peg": {
                   "fair_value": sanitize(peg_fv), 
                   "current_peg": sanitize(company_peg), 
                   "industry_peg": sanitize(sector_median_pe/15.0),
                   "eps_growth_estimated": sanitize(growth_5y),
                   "current_pe": sanitize(current_pe)
               },
               "dcf": {
                   "discount_rate_applied": sanitize(discount_rate * 100),
                   "eps_growth_applied": sanitize(growth_5y),
                   "shares_outstanding": shares,
                   "total_cash": data.get("total_cash", 0),
                   "total_debt": data.get("total_debt", 0),
                   "fcf": fcf,
                   "dcf_perpetual": dcf_perp_mapped,
                   "dcf_exit_multiple": dcf_exit_mapped,
                   "5yr": {
                       "dcf_perpetual": dcf_perp_mapped,
                       "dcf_exit_multiple": dcf_exit_mapped,
                       "eps_growth_applied": sanitize(growth_5y)
                   },
                   "10yr": {
                       "dcf_perpetual": dcf_perp_mapped, # Proxy for now
                       "dcf_exit_multiple": dcf_exit_mapped,
                       "eps_growth_applied": sanitize(growth_5y)
                   },
                   "current_price": float(current_price),
                   "margin_of_safety": sanitize(((vals["dcf"] - current_price)/current_price*100) if vals["dcf"] and current_price>0 else 0)
               },
               "relative": {
                   "fair_value": sanitize(relative_val), 
                   "median_peer_pe": sanitize(sector_median_pe),
                   "mean_peer_pe": sanitize(sector_median_pe), 
                   "company_eps": sanitize(eps_for_valuation),
                   "market_pe_trailing": sanitize(market_data.get("trailing_pe"))
               }
            },
            "historical_anchors": data.get("historical_anchors", []),
            "historical_trends": data.get("historical_trends", []),
            "historical_data": data.get("historical_data", {}),
            "red_flags": data.get("red_flags", []),
            "debug_version": f"{CACHE_VERSION}-ULTRA-STABILITY-FIX",
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        valuation_cache[cache_key] = resp_data
        return deep_clean_data(resp_data)

    except Exception as e:
        print(f"VALUATION CRASH {ticker}: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/watchlist")
def get_watchlist():
    try:
        data = kv_get("watchlist") or []
        return list(set([t.upper() for t in data]))
    except: return []

@app.post("/api/watchlist")
def save_watchlist(req: WatchlistRequest):
    try:
        kv_set("watchlist", req.tickers)
        return {"status": "success"}
    except: return {"status": "error"}

@app.get("/api/overrides")
def get_overrides(): return _load_overrides()

@app.post("/api/overrides")
def save_override(req: OverrideRequest):
    try:
        all_ovr = _load_overrides()
        all_ovr[req.ticker.upper()] = {"inputs": req.inputs, "toggles": req.toggles, "computed": req.computed, "weights": req.weights}
        _save_overrides(all_ovr)
        return {"status": "success"}
    except: return {"status": "error"}

@app.delete("/api/overrides/{ticker}")
def delete_override(ticker: str):
    try:
        all_ovr = _load_overrides()
        if ticker.upper() in all_ovr:
            del all_ovr[ticker.upper()]
            _save_overrides(all_ovr)
        return {"status": "success"}
    except: return {"status": "error"}

@app.post("/api/batch-valuation")
def get_batch_valuation(req: WatchlistRequest):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_valuation, t.upper(), None, None, False, False): t for t in req.tickers}
        for f in concurrent.futures.as_completed(futures):
            try:
                res = f.result()
                if res and not res.get("error"): results.append(res)
            except: pass
    return results

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
