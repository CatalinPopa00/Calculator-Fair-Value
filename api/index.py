import sys
import os
# Correct path for Vercel deployment to find root modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cachetools import TTLCache
import uvicorn
import math
import statistics
from typing import List, Dict, Any, Optional

import urllib.request
import urllib.parse
import json
import os
import requests
import concurrent.futures

from scraper.yahoo import get_company_data, get_competitors_data, get_market_averages, search_companies, get_analyst_data, get_risk_free_rate, get_company_synthesis, _company_info_cache
from utils.kv import kv_get, kv_set
from models.valuation import (
    calculate_peter_lynch, 
    calculate_peg_fair_value, 
    calculate_dcf, 
    calculate_relative_valuation,
    calculate_dcf_sensitivity,
    calculate_reverse_dcf
)
from models.scoring import calculate_scoring_reform, calculate_piotroski_score

# Cache for search results (30 mins TTL)
search_cache = TTLCache(maxsize=500, ttl=30 * 60)
# Valuation cache (1 hour TTL for active development/accuracy)
valuation_cache = TTLCache(maxsize=1000, ttl=60 * 60)
CACHE_VERSION = "v313"
def get_usd_fx_rate(currency: str) -> float:
    if not currency:
        return 1.0
    c_upper = currency.upper().strip()
    if c_upper == 'USD':
        return 1.0
    
    # Handle Pence (GBp/GBX) to USD
    is_pence = False
    if c_upper in ['GBX', 'GBP']:
        c_upper = 'GBP'
        is_pence = True
        
    try:
        import yfinance as yf
        symbol = f"{c_upper}USD=X"
        fx = yf.Ticker(symbol)
        hist = fx.history(period="1d")
        if not hist.empty:
            rate = float(hist['Close'].iloc[-1])
            if is_pence:
                return rate / 100.0
            return rate
    except Exception as e:
        print(f"Error fetching USD FX Rate for {currency}: {e}")
        
    # Fallbacks for common currencies if Yahoo is blocked
    fallbacks = {
        'EUR': 1.08,
        'GBP': 1.25,
        'CAD': 0.73,
        'AUD': 0.66,
        'JPY': 0.0065,
        'CHF': 1.10,
        'CNY': 0.14,
        'RON': 0.22,
        'DKK': 0.14,
        'SEK': 0.095
    }
    rate = fallbacks.get(c_upper, 1.0)
    if is_pence:
        return rate / 100.0
    return rate

# 1. Initialize FastAPI App (Systemic Recovery Fix)
app = FastAPI(title="Fair Value Calculator API")

allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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

class ValuationResponse(BaseModel):
    ticker: str
    name: str = "Unknown"
    current_price: float = 0.0
    fair_value: Optional[float] = None
    margin_of_safety: Optional[float] = None
    dcf_value: Optional[float] = None
    relative_value: Optional[float] = None
    lynch_fwd_pe: Optional[float] = None
    lynch_fair_value: Optional[float] = None
    lynch_status: Optional[str] = None
    peg_value: Optional[float] = None
    recommended_exit_multiple: Optional[float] = None
    company_profile: Optional[dict] = None
    historical_trends: Optional[list] = None
    historical_anchors: Optional[list] = None
    company_overview_synthesis: Optional[str] = None
    formula_data: Dict[str, Any] = {}
    health_score_total: Optional[Any] = None
    health_breakdown: Optional[list] = None
    good_to_buy_total: Optional[Any] = None
    buy_breakdown: Optional[list] = None
    piotroski_score: Optional[Any] = None
    piotroski_breakdown: Optional[list] = None
    historical_data: Optional[dict] = None
    algorithmic_insights: Optional[dict] = None
    red_flags: Optional[list] = None
    overrides: Optional[dict] = None
    competitor_metrics: Optional[list] = None
    
    class Config:
        extra = "allow"



@app.get("/api/search/{query}")
def search(query: str, response: Response):
    # Agresiv cache for search (24h edge, 7d background revalidate)
    response.headers["Cache-Control"] = "public, s-maxage=86400, stale-while-revalidate=604800"
    
    q_key = query.lower().strip()
    if q_key in search_cache:
        return search_cache[q_key]
        
    result = search_companies(query)
    
    # Only cache if we got results, or if the query is very short (likely no results anyway)
    if result or len(q_key) <= 2:
        search_cache[q_key] = result
        
    return result

@app.get("/api/analyst/{ticker}")
def get_analyst(ticker: str, response: Response):
    # Cache analyst data for 1 hour on Edge, background refresh up to 24h
    response.headers["Cache-Control"] = "public, s-maxage=3600, stale-while-revalidate=86400"
    
    ticker_upper = ticker.upper()
    cache_key = f"analyst_v2_{ticker_upper}_{CACHE_VERSION}"
    if cache_key in valuation_cache:
        return valuation_cache[cache_key]
    result = get_analyst_data(ticker_upper)
    # v147 Visible Marker for Diagnostic
    if result and "price_target" in result:
        result["price_target"]["avg"] = str(result["price_target"].get("avg", "")) + " (v147)"
    valuation_cache[cache_key] = result
    return result

@app.get("/api/sector-peers/{ticker}")
def get_sector_peers(ticker: str, response: Response):
    """Fetches top 10 most relevant sector/industry peers with enriched forward metrics."""
    response.headers["Cache-Control"] = "public, s-maxage=3600, stale-while-revalidate=86400"
    
    ticker_upper = ticker.upper()
    cache_key = f"sector_peers_v1_{ticker_upper}_{CACHE_VERSION}"
    
    if cache_key in valuation_cache:
        return valuation_cache[cache_key]
    
    try:
        peers_data = get_competitors_data(ticker_upper, limit=10)
        
        if not peers_data:
            return []
        
        # Enrich each peer with forward metrics (same logic as main valuation endpoint)
        def _calculateForwardEvEbitda(comp_data):
            mcap = comp_data.get("market_cap") or 0
            if mcap <= 0:
                shares = comp_data.get("shares_outstanding") or 0
                price = comp_data.get("price") or comp_data.get("current_price") or 0
                if shares > 0 and price > 0:
                    mcap = shares * price
            debt = comp_data.get("total_debt") or 0
            cash = comp_data.get("total_cash") or 0
            curr_ev = mcap + debt - cash if mcap > 0 else 0
            yahoo_ev = comp_data.get("enterprise_value")
            if yahoo_ev and yahoo_ev > 0:
                curr_ev = yahoo_ev
            if curr_ev <= 0:
                curr_ev = mcap
            fwd_ebitda = comp_data.get("forward_ebitda") or comp_data.get("forwardEbitda")
            if fwd_ebitda and fwd_ebitda > 0 and curr_ev > 0:
                val = curr_ev / fwd_ebitda
                return round(val, 4) if val > 0 else None
            fwd_rev = comp_data.get("forward_revenue")
            ttm_ebitda = comp_data.get("ebitda")
            ttm_rev = comp_data.get("revenue")
            if fwd_rev and ttm_ebitda and ttm_rev and ttm_rev > 0:
                ebitda_margin = ttm_ebitda / ttm_rev
                estimated_fwd_ebitda = fwd_rev * ebitda_margin
                if estimated_fwd_ebitda > 0 and curr_ev > 0:
                    return round(curr_ev / estimated_fwd_ebitda, 4)
            ttm_ev_ebitda = comp_data.get("ev_to_ebitda")
            if ttm_ev_ebitda and ttm_ev_ebitda > 0:
                rev_g = comp_data.get("revenue_growth") or 0
                if rev_g > 0 and rev_g < 1.0:
                    val = ttm_ev_ebitda / (1 + rev_g)
                    return round(val, 4) if val > 0 else None
                else:
                    return round(ttm_ev_ebitda, 4)
            return None

        def _calculateForwardPE(comp_data):
            fwd_eps = comp_data.get("forward_eps") or comp_data.get("fwd_eps")
            price = comp_data.get("price") or comp_data.get("current_price")
            if fwd_eps and price and fwd_eps > 0:
                val = price / fwd_eps
                return round(val, 4) if val > 0 else None
            return None

        def _calculateForwardEvSales(comp_data):
            mcap = comp_data.get("market_cap") or 0
            debt = comp_data.get("total_debt") or 0
            cash = comp_data.get("total_cash") or 0
            if mcap <= 0:
                shares = comp_data.get("shares_outstanding") or 0
                price = comp_data.get("price") or comp_data.get("current_price") or 0
                if shares > 0 and price > 0:
                    mcap = shares * price
            if mcap <= 0:
                return None
            ev = mcap + debt - cash
            if ev <= 0:
                ev = mcap
            fwd_rev = comp_data.get("forward_revenue")
            if not fwd_rev or fwd_rev <= 0:
                rev = comp_data.get("revenue")
                g = comp_data.get("revenue_growth")
                if rev and rev > 0 and g is not None:
                    fwd_rev = rev * (1 + g)
            if not fwd_rev or fwd_rev <= 0:
                fwd_rev = comp_data.get("revenue")
            if fwd_rev and fwd_rev > 0:
                return ev / fwd_rev
            return None

        def sanitize(val):
            if val is None:
                return None
            if isinstance(val, (int, float)):
                if not math.isfinite(val):
                    return None
                return val
            return val

        enriched = []
        for p in peers_data:
            p['forward_ev_ebitda'] = _calculateForwardEvEbitda(p)
            p['forward_pe'] = _calculateForwardPE(p)
            p['forward_ev_sales'] = _calculateForwardEvSales(p)
            
            # cagr_5y_custom and peg_custom are preserved from scraper
            
            enriched.append({
                "ticker": p.get("ticker"),
                "name": p.get("name"),
                "price": sanitize(p.get("price")),
                "market_cap": sanitize(p.get("market_cap")),
                "pe_ratio": sanitize(p.get("pe_ratio")),
                "forward_pe": sanitize(p.get("forward_pe")),
                "peg_ratio": sanitize(p.get("peg_ratio")),
                "eps": sanitize(p.get("eps")),
                "forward_eps": sanitize(p.get("forward_eps")),
                "ps_ratio": sanitize(p.get("ps_ratio")),
                "forward_ev_sales": sanitize(p.get("forward_ev_sales")),
                "price_to_book": sanitize(p.get("price_to_book")),
                "ev_to_ebitda": sanitize(p.get("ev_to_ebitda")),
                "forward_ev_ebitda": sanitize(p.get("forward_ev_ebitda")),
                "revenue": sanitize(p.get("revenue")),
                "forward_revenue": sanitize(p.get("forward_revenue")),
                "fcf": sanitize(p.get("fcf")),
                "pfcf_ratio": sanitize(p.get("pfcf_ratio")),
                "operating_margin": sanitize(p.get("operating_margin")),
                "revenue_growth": sanitize(p.get("revenue_growth")),
                "earnings_growth": sanitize(p.get("earnings_growth")),
                "shares_outstanding": sanitize(p.get("shares_outstanding")),
                "total_cash": sanitize(p.get("total_cash")),
                "total_debt": sanitize(p.get("total_debt")),
                "sector": p.get("sector"),
                "industry": p.get("industry"),
                "avg_2y_eps_growth": sanitize(p.get("avg_2y_eps_growth")),
                "forward_peg": sanitize(p.get("forward_peg")),
                "forward_pe_custom": sanitize(p.get("forward_pe_custom")),
                "cagr_5y_custom": sanitize(p.get("cagr_5y_custom")),
                "peg_custom": sanitize(p.get("peg_custom")),
                "ps_forward_custom": sanitize(p.get("ps_forward_custom")),
                "fcf_margin_custom": sanitize(p.get("fcf_margin_custom")),
                "pfcf_forward_custom": sanitize(p.get("pfcf_forward_custom")),
            })
        
        valuation_cache[cache_key] = enriched
        return enriched
    except Exception as e:
        print(f"DEBUG: sector-peers error for {ticker_upper}: {e}")
        return []

# KV functions moved to .utils.kv

@app.get("/api/watchlist")
def get_watchlist():
    try:
        data = kv_get("watchlist") or []
        # Overrides should not be forced into the watchlist. Watchlist should remain exactly as saved by the user.
        
        if not data and os.path.exists(WATCHLIST_FILE):
            try:
                with open(WATCHLIST_FILE, "r") as f:
                    data = json.load(f)
            except:
                pass
        return list(set([t.upper() for t in data]))
    except Exception as e:
        # v37 Fix: If database errors, do NOT return []. Return 500.
        print(f"Database error in get_watchlist: {e}")
        raise HTTPException(status_code=500, detail="Database unreachable")

@app.post("/api/watchlist")
def save_watchlist(req: WatchlistRequest):
    try:
        kv_set("watchlist", req.tickers)
        try:
            with open(WATCHLIST_FILE, "w") as f:
                json.dump(req.tickers, f)
        except:
            pass
        return {"status": "success"}
    except Exception as e:
        print(f"Error saving watchlist: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# --- Overrides API (cross-device sync) ---
def _load_overrides() -> dict:
    data = kv_get("overrides")
    if data is not None:
        return data

    if os.path.exists(OVERRIDES_FILE):
        try:
            with open(OVERRIDES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_overrides(data: dict):
    kv_set("overrides", data)
    try:
        with open(OVERRIDES_FILE, "w") as f:
            json.dump(data, f)
    except:
        pass

@app.get("/api/overrides")
def get_overrides():
    return _load_overrides()

@app.post("/api/overrides")
def save_override(req: OverrideRequest):
    try:
        all_overrides = _load_overrides()
        all_overrides[req.ticker.upper()] = {
            "inputs": req.inputs,
            "toggles": req.toggles,
            "computed": req.computed,
            "weights": req.weights
        }
        _save_overrides(all_overrides)
        return {"status": "success"}
    except Exception as e:
        print(f"Error saving override: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/overrides/{ticker}")
def delete_override(ticker: str):
    try:
        all_overrides = _load_overrides()
        ticker_upper = ticker.upper()
        if ticker_upper in all_overrides:
            del all_overrides[ticker_upper]
            _save_overrides(all_overrides)
        return {"status": "success"}
    except Exception as e:
        print(f"Error deleting override: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def get_recommended_exit_multiple(sector: str, industry: str) -> float:
    """Assigns recommended exit multiple based on sector/industry (User Strict Rule Refinement)."""
    s = str(sector).lower()
    ind = str(industry).lower()
    
    # 1. Premium: Technology, Software, Healthcare, Communication Services
    if any(x in s for x in ["tech", "soft", "health", "communication"]):
        return 15.0
    
    # 2. Defensive: Consumer Defensive, Utilities, Consumer Staples
    if any(x in s for x in ["defensive", "utilities", "staple"]):
        return 12.0
    
    # 3. Cyclical / Heavy: Energy, Oil & Gas, Basic Materials, Industrials, Auto, Manufacturing
    if any(x in s for x in ["energy", "oil", "gas", "material", "industrial", "manufacturing"]) or "auto" in ind:
        return 8.0
        
    # 4. Financials / REITs: Financials, Banks, Insurance, Real Estate, REITs
    if any(x in s for x in ["financial", "bank", "insurance", "real estate", "reit"]):
        return 10.0
        
    return 10.0

def deep_clean_data(val):
    if isinstance(val, dict):
        return {k: deep_clean_data(v) for k, v in val.items()}
    if isinstance(val, list):
        return [deep_clean_data(v) for v in val]
    if hasattr(val, "item"): # Handle numpy scalars
        return val.item()
    if isinstance(val, (int, float)):
        if not math.isfinite(val): return None
        return val
    if isinstance(val, (str, bool)) or val is None:
        return val
    return str(val)

@app.get("/api/valuation/{ticker}")
def get_valuation(ticker: str, response: Response, wacc: float = None, fast_mode: bool = False, skip_peers: bool = False, force_refresh: bool = False):
    # Set Vercel Edge Cache headers for pseudo-ISR (Cache 1hr, stale up to 24hr)
    if force_refresh:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    else:
        response.headers["Cache-Control"] = "public, s-maxage=3600, stale-while-revalidate=86400"
    
    # GOD MODE: Pre-initialize all possible response keys to Safe Defaults (v55)
    ticker_upper = ticker.upper()
    current_price = 0.0
    fair_value = None
    margin_of_safety = None
    dcf_value = None
    relative_value = None
    lynch_fwd_pe = None
    lynch_fair_value = None
    lynch_status = "N/A"
    peg_value = None
    recommended_exit_multiple = 15.0
    formula_data = {}
    health_score_total = "N/A"
    health_breakdown = []
    good_to_buy_total = "N/A"
    buy_breakdown = []
    piotroski_score = "N/A"
    piotroski_breakdown = []
    top_strengths = []
    risk_factors = []
    red_flags = []
    peers_data = []
    median_peer_pe = 20.0
    median_peer_peg = 1.0
    eps_for_valuation = 0.0
    current_pe = 0.0
    rec_exit_mult = 15.0
    dcf_val_final = None
    fair_value_total = None
    
    try:
        # Ensure wacc is normalized for the key
        norm_wacc = round(float(wacc), 2) if wacc is not None else "def"
        # Synchronized v38: Always include skip_peers to prevent cache collision
        cache_key = f"valuation_{ticker.upper()}_{fast_mode}_{skip_peers}_{CACHE_VERSION}_{norm_wacc}"
        
        # 0. Cache Elevation: If we are in any limited mode (Watchlist/SkipPeers), 
        # Always check if we have a full_mode cache (Complete Data) in memory first.
        if (fast_mode or skip_peers) and not force_refresh:
            full_mode_key = f"valuation_{ticker.upper()}_False_False_{CACHE_VERSION}_{norm_wacc}"
            if full_mode_key in valuation_cache:
                return valuation_cache[full_mode_key]

        # 1. Persistent Cache Check
        persistent_cache_key = f"val_data_v30_{ticker.upper()}"
        cached_data = kv_get(persistent_cache_key)
        if cached_data and not force_refresh:
            return cached_data
            
        persistent_skip_key = f"val_data_v30_skip_{ticker.upper()}"
        if skip_peers:
            cached_skip = kv_get(persistent_skip_key)
            if cached_skip and not force_refresh:
                return cached_skip

        # 2. Local Memory Cache check for the specific requested mode
        if not force_refresh and cache_key in valuation_cache:
            return valuation_cache[cache_key]

        # v41: THE PARALLEL BLITZ
        # Run main scraping and peer fetching simultaneously to cut wait time in half.
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        # 1. Start main scraper
        main_task = executor.submit(get_company_data, ticker_upper, fast_mode, force_refresh)
        
        # Dynamic Peers Launch (Skip if skip_peers is True)
        future_peers = None
        if not skip_peers:
            future_peers = executor.submit(get_competitors_data, ticker_upper, 4, None, force_refresh)
        
        # 6. Sector Metrics & Dynamic Benchmarks
        try:
            # get_market_averages takes no arguments (returns SPY PE)
            market_averages = get_market_averages()
            sector_metrics = {"market_pe": market_averages.get("trailing_pe") if isinstance(market_averages, dict) else 15.0}
        except Exception as e:
            print(f"Error computing sector metrics: {e}")
            sector_metrics = {}
        
        # Wait for main data with robust error handling
        try:
            data = main_task.result() or {}
        except Exception as e:
            print(f"DEBUG: Main scraper task failed for {ticker_upper}: {e}")
            data = {"ticker": ticker_upper, "error": "Ticker analysis failed due to an internal error."}
        
        # v296: Early exit if ticker is definitively not found (Bypasses 500 crashes)
        if not data or data.get("error") or (not data.get("current_price") and not data.get("name")):
            detail_msg = data.get("error") or f"Ticker '{ticker_upper}' not found or has no active trade data."
            return JSONResponse(
                status_code=404,
                content={"error": True, "detail": detail_msg, "ticker": ticker_upper}
            )

        # --- DYNAMIC FX CURRENCY CONVERSION TO USD ---
        price_currency = data.get("currency", "USD")
        price_fx = get_usd_fx_rate(price_currency)
        
        if price_fx != 1.0:
            # Convert price-dependent metrics
            if data.get("current_price"): 
                data["current_price"] = data["current_price"] * price_fx
            if data.get("price_target"):
                pt = data["price_target"]
                for pt_key in ["low", "avg", "median", "high"]:
                    if pt.get(pt_key) is not None:
                        pt[pt_key] = pt[pt_key] * price_fx
            
            # Convert financial-dependent metrics (already normalized to price_currency by scraper)
            for key in ["adjusted_eps", "trailing_eps", "fwd_eps", "forward_eps", "fcf", "total_cash", "total_debt", "revenue", "forward_revenue", "ebitda", "eps_last_year"]:
                if data.get(key) is not None:
                    data[key] = data[key] * price_fx
            
            # Convert eps_trend
            if data.get("eps_trend"):
                for period, trend in data["eps_trend"].items():
                    if isinstance(trend, dict):
                        for metric in ["avg", "low", "high", "yearAgoEps", "current"]:
                            if trend.get(metric) is not None:
                                trend[metric] = trend[metric] * price_fx
            
            # Convert multi-year eps estimates
            if data.get("eps_estimates"):
                for est in data["eps_estimates"]:
                    if est.get("avg") is not None:
                        est["avg"] = est["avg"] * price_fx
                    if est.get("low") is not None:
                        est["low"] = est["low"] * price_fx
                    if est.get("high") is not None:
                        est["high"] = est["high"] * price_fx
                        
            # Convert multi-year revenue estimates
            if data.get("rev_estimates"):
                for est in data["rev_estimates"]:
                    if est.get("avg") is not None:
                        est["avg"] = est["avg"] * price_fx
                    if est.get("low") is not None:
                        est["low"] = est["low"] * price_fx
                    if est.get("high") is not None:
                        est["high"] = est["high"] * price_fx
            
            # Convert historical data
            if data.get("historical_data"):
                for h_key in ["revenue", "eps", "diluted_eps", "fcf"]:
                    if data["historical_data"].get(h_key):
                        data["historical_data"][h_key] = [v * price_fx if v is not None else None for v in data["historical_data"][h_key]]
                        
            # Convert raw_quarterly_history
            if data.get("raw_quarterly_history"):
                for year, quarters in data["raw_quarterly_history"].items():
                    if isinstance(quarters, dict):
                        for date, q_data in quarters.items():
                            if isinstance(q_data, list) and len(q_data) > 0 and q_data[0] is not None:
                                q_data[0] = q_data[0] * price_fx
        
        # Recalculate forward ratios in USD to prevent currency mismatch
        shares = data.get("shares_outstanding") or 1
        rev_per_share = (data.get("revenue") or 0) / shares if shares else 0
        
        # Recalculate fwd_pe if we have fy1_eps in USD
        if data.get("eps_estimates") and data.get("current_price"):
            fy1 = next((e for e in data["eps_estimates"] if e.get("period") == "FY 1" or "FY1" in str(e.get("period"))), None)
            if fy1 and fy1.get("avg") and fy1.get("avg") > 0:
                data["fwd_pe"] = data["current_price"] / fy1["avg"]
                
        # Recalculate fwd_ps if we have fy1_rev in USD
        if data.get("rev_estimates") and data.get("current_price") and shares:
            fy1_r = next((e for e in data["rev_estimates"] if e.get("period") == "FY 1" or "FY1" in str(e.get("period"))), None)
            if fy1_r and fy1_r.get("avg") and fy1_r.get("avg") > 0:
                fy1_rev_share = fy1_r["avg"] / shares
                data["fwd_ps"] = data["current_price"] / fy1_rev_share if fy1_rev_share > 0 else None

        # Get peer data with timeout protection
        peers_data = []
        if future_peers:
            try:
                peers_data = future_peers.result(timeout=12) or []
            except Exception as e:
                print(f"DEBUG: Parallel peer fetch failed for {ticker_upper}: {e}")
                peers_data = []
                
        # Strict Forward Proxy Functions (v308: Robust multi-fallback)
        def calculateForwardPS(comp_data):
            """Forward Price-to-Sales: mcap / forward_revenue"""
            mcap = comp_data.get("market_cap") or 0
            if mcap <= 0:
                shares = comp_data.get("shares_outstanding") or 0
                price = comp_data.get("price") or comp_data.get("current_price") or 0
                if shares > 0 and price > 0:
                    mcap = shares * price
            
            if mcap <= 0:
                return None
            
            fwd_rev = comp_data.get("forward_revenue")
            if not fwd_rev or fwd_rev <= 0:
                rev = comp_data.get("revenue")
                g = comp_data.get("revenue_growth")
                if rev and rev > 0 and g is not None:
                    fwd_rev = rev * (1 + g)
            
            if not fwd_rev or fwd_rev <= 0:
                fwd_rev = comp_data.get("revenue")
            
            if fwd_rev and fwd_rev > 0:
                return mcap / fwd_rev
            return None
        def calculateForwardEvSales(comp_data):
            """Forward EV-to-Sales: EV / forward_revenue"""
            mcap = comp_data.get("market_cap") or 0
            debt = comp_data.get("total_debt") or 0
            cash = comp_data.get("total_cash") or 0
            
            if mcap <= 0:
                shares = comp_data.get("shares_outstanding") or 0
                price = comp_data.get("price") or comp_data.get("current_price") or 0
                if shares > 0 and price > 0:
                    mcap = shares * price
            
            if mcap <= 0:
                return None
                
            ev = mcap + debt - cash
            # If cash is massive, EV could be negative. Cap at mcap for sanity in multiples.
            if ev <= 0:
                ev = mcap

            fwd_rev = comp_data.get("forward_revenue")
            if not fwd_rev or fwd_rev <= 0:
                rev = comp_data.get("revenue")
                g = comp_data.get("revenue_growth")
                if rev and rev > 0 and g is not None:
                    fwd_rev = rev * (1 + g)
            if not fwd_rev or fwd_rev <= 0:
                fwd_rev = comp_data.get("revenue")

            
            if fwd_rev and fwd_rev > 0:
                return ev / fwd_rev
            return None

        def calculateForwardEvEbitda(comp_data):
            """Forward EV/EBITDA with 3-level fallback:
               1) Use forward_ebitda if available
               2) Estimate fwd EBITDA from forward_eps * shares + (EBITDA - NI) spread
               3) Use Yahoo TTM ev_to_ebitda and adjust for earnings growth
            """
            mcap = comp_data.get("market_cap") or 0
            if mcap <= 0:
                shares = comp_data.get("shares_outstanding") or 0
                price = comp_data.get("price") or comp_data.get("current_price") or 0
                if shares > 0 and price > 0:
                    mcap = shares * price
            
            debt = comp_data.get("total_debt") or 0
            cash = comp_data.get("total_cash") or 0
            curr_ev = mcap + debt - cash if mcap > 0 else 0

            # Use enterprise_value from Yahoo if available (more accurate)
            yahoo_ev = comp_data.get("enterprise_value")
            if yahoo_ev and yahoo_ev > 0:
                curr_ev = yahoo_ev
            
            if curr_ev <= 0:
                curr_ev = mcap  # Last resort: use mcap as EV proxy

            # --- Attempt 1: Direct forward_ebitda ---
            fwd_ebitda = comp_data.get("forward_ebitda") or comp_data.get("forwardEbitda")
            if fwd_ebitda and fwd_ebitda > 0 and curr_ev > 0:
                val = curr_ev / fwd_ebitda
                return round(val, 4) if val > 0 else None

            # --- Attempt 2: Estimate via Forward Revenue & EBITDA Margin ---
            fwd_rev = comp_data.get("forward_revenue")
            ttm_ebitda = comp_data.get("ebitda")
            ttm_rev = comp_data.get("revenue")
            
            if fwd_rev and ttm_ebitda and ttm_rev and ttm_rev > 0:
                ebitda_margin = ttm_ebitda / ttm_rev
                estimated_fwd_ebitda = fwd_rev * ebitda_margin
                if estimated_fwd_ebitda > 0 and curr_ev > 0:
                    val = curr_ev / estimated_fwd_ebitda
                    return round(val, 4)

            # --- Attempt 3: TTM EV/EBITDA adjusted for revenue growth ---
            ttm_ev_ebitda = comp_data.get("ev_to_ebitda")
            if ttm_ev_ebitda and ttm_ev_ebitda > 0:
                # Use revenue_growth as a much safer proxy for EBITDA growth
                rev_g = comp_data.get("revenue_growth") or 0
                if rev_g > 0 and rev_g < 1.0: # Cap adjustment at 100%
                    # Forward = TTM / (1 + growth) 
                    val = ttm_ev_ebitda / (1 + rev_g)
                    return round(val, 4) if val > 0 else None
                else:
                    return round(ttm_ev_ebitda, 4)

            return None

        def calculateForwardPE(comp_data):
            fwd_eps = comp_data.get("forward_eps") or comp_data.get("fwd_eps")
            price = comp_data.get("price") or comp_data.get("current_price")
            if fwd_eps and price and fwd_eps > 0:
                val = price / fwd_eps
                return round(val, 4) if val > 0 else None
            return None

        # Dynamic peer calculations
        data['forward_ps'] = calculateForwardPS(data)
        data['forward_ev_sales'] = calculateForwardEvSales(data)
        data['forward_ev_ebitda'] = calculateForwardEvEbitda(data)
        data['forward_pe'] = calculateForwardPE(data)
        
        # cagr_5y_custom and peg_custom are preserved from scraper
            
        # Unify the profile's fwd_ps to use the robust Forward P/S
        if data.get('forward_ps'):
            data['fwd_ps'] = data['forward_ps']
        
        if peers_data:
            for p in peers_data:
                p_price = p.get("price")
                p_eps = p.get("eps")
                if p_price and p_eps and p_eps > 0:
                    p["pe_ratio"] = p_price / p_eps
                p_pe = p.get("pe_ratio")
                p_growth = p.get("earnings_growth") or p.get("revenue_growth")
                if not p.get("peg_ratio") and p_pe and p_growth and p_growth > 0:
                    p["peg_ratio"] = p_pe / (p_growth * 100.0)
                
                # Apply proxies for peers
                p['forward_ev_sales'] = calculateForwardEvSales(p)
                p['forward_ev_ebitda'] = calculateForwardEvEbitda(p)
                p['forward_pe'] = calculateForwardPE(p)

                # custom metrics are preserved from scraper
                

        executor.shutdown(wait=False)

        # FINAL STRIKE: Graceful recovery if Yahoo is blocked or null
        current_price = data.get("current_price") or 0.0
        if not data.get("name"):
            data["name"] = ticker.upper()
        
        # v251: Ensure ticker is strictly ticker, don't allow doubling
        data["ticker"] = ticker.upper()
    
        all_overrides = _load_overrides()
        ticker_overrides = all_overrides.get(ticker.upper())
        sector = data.get("sector")
        industry = data.get("industry")
        target_market_cap = data.get("market_cap") or 0.0

        # v92 Fix: Define historical_anchors (missing variable causing 500)
        historical_anchors = data.get("historical_anchors", [])

        # Watchlist skips expensive peer fetching to save 80% loading time while retaining sync
        market_data = get_market_averages()
        
        # 3. Compute Valuations (v219: Use recalculated eps_growth = Avg FY0+FY1 from Normalized Anchors)
        consensus_growth = data.get("eps_growth")
        if consensus_growth is None or consensus_growth <= 0:
            consensus_growth = data.get("eps_growth_5y_consensus") or data.get("eps_growth_3y") or data.get("eps_growth_5y") or 0.05
        
        # Use a safe growth baseline for labels
        eps_growth_estimated = consensus_growth
        
        lynch_period_label = data.get("eps_growth_period") or "2Y EPS CAGR"
        
        
        # Calculate Industry Median PE for Peter Lynch fallback
        valid_pes = []
        if peers_data:
            for p in peers_data:
                v = p.get('pe_ratio')
                if v and isinstance(v, (int, float)) and v > 0:
                    valid_pes.append(v)
        # Include current company PE if available
        if data.get("pe_ratio") and data.get("pe_ratio") > 0:
            valid_pes.append(data.get("pe_ratio"))
            
        sector_median_pe = statistics.median(valid_pes) if valid_pes else 20.0
        median_peer_pe = sector_median_pe

        pe_historic = data.get("pe_historic") or data.get("pe_ratio")
        
        # STRICT DATA MAPPING: Prioritize Adjusted (Non-GAAP) EPS for valuation models (v70)
        # Trailing TTM EPS fallback only if Adjusted is missing.
        eps_for_valuation = data.get("adjusted_eps") or data.get("trailing_eps", 0) 
        
        # Peter Lynch - Conservative Guardrails for Negative Growth
        # Standard Lynch PE is 20, but for shrinking companies (<0% growth), we cap it at 12x (Risk Adjusted)
        effective_lynch_pe = sector_median_pe
        if consensus_growth < 0:
            effective_lynch_pe = min(sector_median_pe, 12.0)
            
        lynch_result = calculate_peter_lynch(current_price, eps_for_valuation, consensus_growth, pe_historic, effective_lynch_pe)
        lynch_fwd_pe = lynch_result.get("fwd_pe")
        lynch_fair_value = lynch_result.get("fair_value")
        lynch_status = lynch_result.get("status")

        # Additional Benchmarks for Data Transparency
        res_pe20 = calculate_peter_lynch(current_price, eps_for_valuation, consensus_growth, pe_historic, 20.0)
        lynch_pe20_val = res_pe20.get("fair_value")
        
        res_sector = calculate_peter_lynch(current_price, eps_for_valuation, consensus_growth, pe_historic, sector_median_pe)
        fair_value_sector_pe = res_sector.get("fair_value")
        
        # PEG Valuation (Sector-based)
        eps_base = data.get("adjusted_eps")
        peg_eps_type = "Non-GAAP"
        if eps_base is None or eps_base <= 0:
            eps_base = data.get("trailing_eps", 0)
            peg_eps_type = "GAAP"
            
        current_pe = current_price / eps_base if eps_base > 0 else 0
        
        # Fallback logic handled by consensus_growth
        eps_growth_rate_peg = consensus_growth
        
        peg_period_label = data.get("eps_growth_period") or "2Y EPS CAGR"
        company_peg = current_pe / (eps_growth_rate_peg * 100) if eps_growth_rate_peg > 0 else 0
        
        # Export the flag and custom metrics
        data["peg_eps_type"] = peg_eps_type
        # company_peg is preserved or used only for backwards compat
        data["peg_custom"] = data.get('peg_custom') or company_peg
        
        # Calculate Industry PEG from peers using Forward PEG (2Y avg EPS growth based)
        valid_pegs = []
        
        if peers_data:
            for p in peers_data:
                p_price = p.get('price')
                p_eps = p.get('adjusted_eps')
                peer_peg_type = "Non-GAAP"
                if p_eps is None or p_eps <= 0:
                    p_eps = p.get('eps')
                    peer_peg_type = "GAAP"
                    
                if p_price and p_eps and p_eps > 0:
                    p_pe = p_price / p_eps
                    p['pe_non_gaap'] = p_pe
                else:
                    p_pe = None
                    
                p_growth = p.get("earnings_growth") or p.get("revenue_growth")
                # Calculate peer PEG exactly like company PEG
                if p_pe and p_pe > 0 and p_growth and p_growth > 0:
                    p_peg = p_pe / (p_growth * 100.0)
                    valid_pegs.append(float(p_peg))
                    p['peg_eps_type'] = peer_peg_type
                else:
                    # Fallback to Yahoo's 5Y PEG if we lack growth data
                    p_peg = p.get('peg_ratio')
                    if p_peg and p_peg > 0:
                        valid_pegs.append(float(p_peg))
                        p['peg_eps_type'] = peer_peg_type
        
        # No fallback, return None if no valid peers
        industry_peg = statistics.median(valid_pegs) if valid_pegs else None
        peg_value = calculate_peg_fair_value(current_price, company_peg, industry_peg)
        
        # Multi-Metric Sector-Weighted Relative Valuation (Strict Forward)
        company_shares = data.get("shares_outstanding") or 1
        company_debt = data.get("total_debt") or 0
        company_cash = data.get("total_cash") or 0
        company_book_val = data.get("book_value") or (data.get("book_value_per_share") * company_shares if data.get("book_value_per_share") and company_shares else 0)
        company_book_share = (company_book_val / company_shares) if company_book_val and company_shares else (data.get("book_value_per_share") or 0)
        
        # Calculate Target Company Forward Metrics
        targ_fwd_eps = data.get("forward_eps") or data.get("eps")
        targ_fwd_rev = data.get("forward_revenue")
        if targ_fwd_rev is None or targ_fwd_rev <= 0:
            tr = data.get("revenue")
            tg = data.get("next_3y_rev_growth")
            if tr and tr > 0 and tg is not None:
                targ_fwd_rev = tr * (1 + tg)
                
        targ_ebitda = data.get("ebitda") or 0
        targ_ni = data.get("net_income") or (data.get("adjusted_eps") * company_shares if data.get("adjusted_eps") else 0)
        
        bPE = None
        bEVSALES = None
        bEVEBITDA = None
        bPB = None
        
        # We need to compute median beforehand since we extracted the relative logic
        def get_clean_median_local(key):
            vals = []
            if peers_data:
                for p in peers_data:
                    v = p.get(key)
                    if v is not None and isinstance(v, (int, float)) and math.isfinite(v) and v > 0:
                        vals.append(float(v))
            if not vals:
                return None
            return statistics.median(vals)

        bPE = get_clean_median_local('pe_ratio')
        bEVSALES = get_clean_median_local('ps_ratio')
        bEVEBITDA = get_clean_median_local('ev_to_ebitda')
        bPB = get_clean_median_local('price_to_book')
        
        # 1. Forward P/E Fair Value
        fvPE = (targ_fwd_eps * bPE) if (targ_fwd_eps and bPE and targ_fwd_eps > 0) else None
        
        # 2. Forward EV/Sales Fair Value
        fvEVSALES = None
        if targ_fwd_rev and bEVSALES and targ_fwd_rev > 0:
            implied_ev_sales = targ_fwd_rev * bEVSALES
            implied_mcap_sales = implied_ev_sales - company_debt + company_cash
            fvEVSALES = implied_mcap_sales / company_shares if company_shares > 0 else None
            if fvEVSALES is not None and fvEVSALES <= 0: fvEVSALES = None

        # 3. Forward EV/EBITDA Fair Value
        fvEVEBITDA = None
        if targ_fwd_eps and company_shares > 0:
            est_fwd_ni = targ_fwd_eps * company_shares
            tax_int_da = targ_ebitda - targ_ni
            est_fwd_ebitda = est_fwd_ni + tax_int_da
            if est_fwd_ebitda > 0 and bEVEBITDA:
                implied_ev_ebitda = est_fwd_ebitda * bEVEBITDA
                implied_mcap_ebitda = implied_ev_ebitda - company_debt + company_cash
                fvEVEBITDA = implied_mcap_ebitda / company_shares if company_shares > 0 else None
                if fvEVEBITDA is not None and fvEVEBITDA <= 0: fvEVEBITDA = None
                
        # 4. Current P/B Fair Value (Financials only)
        fvPB = (company_book_share * bPB) if (company_book_share and bPB and company_book_share > 0) else None

        SECTOR_WEIGHTS = {
            'Technology': { "PE": 0.35, "EV_EBITDA": 0.50, "EV_SALES": 0.15 },
            'Information Technology': { "PE": 0.35, "EV_EBITDA": 0.50, "EV_SALES": 0.15 },
            'Technology_Growth': { "PE": 0.00, "EV_EBITDA": 0.00, "EV_SALES": 1.00 },
            'Financial Services': { "PE": 0.40, "PB": 0.60 },
            'Financials': { "PE": 0.40, "PB": 0.60 },
            'Industrials': { "PE": 0.20, "EV_EBITDA": 0.80 },
            'Energy': { "PE": 0.20, "EV_EBITDA": 0.80 },
            'Consumer Defensive': { "PE": 0.50, "EV_EBITDA": 0.30, "EV_SALES": 0.20 },
            'Consumer Staples': { "PE": 0.50, "EV_EBITDA": 0.30, "EV_SALES": 0.20 },
            'Consumer Cyclical': { "PE": 0.35, "EV_EBITDA": 0.35, "EV_SALES": 0.30 },
            'Consumer Discretionary': { "PE": 0.35, "EV_EBITDA": 0.35, "EV_SALES": 0.30 },
            'Healthcare': { "PE": 0.35, "EV_EBITDA": 0.40, "EV_SALES": 0.25 },
            'Health Care': { "PE": 0.35, "EV_EBITDA": 0.40, "EV_SALES": 0.25 },
            'Communication Services': { "PE": 0.35, "EV_EBITDA": 0.40, "EV_SALES": 0.25 },
            'Utilities': { "PE": 0.50, "EV_EBITDA": 0.50 },
            'Basic Materials': { "PE": 0.25, "EV_EBITDA": 0.75 },
            'Materials': { "PE": 0.25, "EV_EBITDA": 0.75 },
            'Real Estate': { "PE": 0.00, "P_FFO": 0.80, "P_AFFO": 0.20 },
            'Default': { "PE": 0.40, "EV_EBITDA": 0.40, "EV_SALES": 0.20 }
        }

        sector_name = sector or 'Default'
        weights = SECTOR_WEIGHTS.get(sector_name) or SECTOR_WEIGHTS.get('Default')
        
        # Dynamic Technology_Growth rule:
        if (sector_name == 'Technology' or sector_name == 'Information Technology') and (not targ_fwd_eps or targ_fwd_eps <= 0 or not bPE or bPE > 50):
            weights = { "PE": 0.00, "EV_SALES": 1.00 }
            
        if sector_name not in SECTOR_WEIGHTS:
            if 'Tech' in sector_name: weights = SECTOR_WEIGHTS['Technology']
            elif 'Finance' in sector_name or 'Bank' in sector_name: weights = SECTOR_WEIGHTS['Financial Services']
            elif 'Industrial' in sector_name: weights = SECTOR_WEIGHTS['Industrials']
            elif 'Energy' in sector_name: weights = SECTOR_WEIGHTS['Energy']
            elif 'Health' in sector_name: weights = SECTOR_WEIGHTS['Healthcare']
            elif 'Real Estate' in sector_name or 'REIT' in sector_name: weights = SECTOR_WEIGHTS['Real Estate']
            elif 'Communication' in sector_name: weights = SECTOR_WEIGHTS['Communication Services']
            elif 'Utilit' in sector_name: weights = SECTOR_WEIGHTS['Utilities']
            elif 'Material' in sector_name: weights = SECTOR_WEIGHTS['Materials']

        weightedSum = 0.0
        totalWeight = 0.0
        
        def calcMetric(val, w):
            nonlocal weightedSum, totalWeight
            if w is not None and w > 0:
                if val is not None and math.isfinite(val) and val > 0:
                    weightedSum += val * w
                    totalWeight += w

        if weights.get("PE") is not None: calcMetric(fvPE, weights.get("PE"))
        if weights.get("EV_SALES") is not None: calcMetric(fvEVSALES, weights.get("EV_SALES"))
        if weights.get("EV_EBITDA") is not None: calcMetric(fvEVEBITDA, weights.get("EV_EBITDA"))
        if weights.get("PB") is not None: calcMetric(fvPB, weights.get("PB"))
        
        if weights.get("P_FFO") is not None: calcMetric(fvPE, weights.get("P_FFO"))
        if weights.get("P_AFFO") is not None: calcMetric(fvPE, weights.get("P_AFFO"))

        if totalWeight > 0:
            relative_value = weightedSum / totalWeight
        else:
            relative_value = None
        
        # DCF Exit Multiple Mapping
        recommended_exit_multiple = get_recommended_exit_multiple(sector, industry)
        
        # DCF
        # For DCF, we need FCF, Growth, WACC (discount_rate), terminal growth
        fcf = data.get("fcf")
        shares = data.get("shares_outstanding")
        # We will use simple defaults if missing
        # For DCF, we strictly use the consensus_growth (v62 fix for growing FCF in negative scenarios)
        eps_growth = consensus_growth
        
        dcf_value = None
        dcf_5yr = None
        dcf_10yr = None
    
        # Dynamic WACC (CAPM)
        risk_free_rate = get_risk_free_rate()
        erp = 0.055 # Equity Risk Premium fallback
        beta = data.get("beta")
        if beta is None:
            beta = 1.0 # Default beta
            
        dynamic_wacc = risk_free_rate + (beta * erp)
        
        # Use custom WACC if provided by frontend, else dynamic_wacc
        discount_rate = (wacc / 100.0) if wacc is not None else dynamic_wacc
        perpetual_growth = 0.02 # 2% GDP growth standard
        
        # Initialize variables before conditional assignment to avoid UnboundLocalError
        dcf_cash = data.get("total_cash") or 0
        dcf_debt = data.get("total_debt") or 0
        
        # EXIT MULTIPLE CAP: If growth is negative, cap exit multiple to 12.0 for prudence
        if eps_growth < 0:
            recommended_exit_multiple = min(recommended_exit_multiple or 15.0, 12.0)

        if fcf and shares and fcf > 0:
            # Standard DCF EV = PV(FCF) + Cash - Debt is highly misleading because Cash often includes customer money.
            # For these, we use PV(FCF) as a proxy for Equity Value directly.
            # v63: Only apply to actual Banks/Insurance, not Data/FinTech providers like FDS or MSCI.
            is_bank_or_insurance = any(x in str(industry).lower() for x in ["bank", "insurance", "savings", "credit"])
            if sector == "Financial Services" and is_bank_or_insurance:
                dcf_cash = 0
                dcf_debt = 0
                
        # 5 Year Calculation (Default for Dashboard)
        res_5 = calculate_dcf(fcf, eps_growth, discount_rate, perpetual_growth, shares, dcf_cash, dcf_debt, years=5, exit_multiple=recommended_exit_multiple, current_price=current_price)
        sens_5 = calculate_dcf_sensitivity(fcf, eps_growth, shares, dcf_cash, dcf_debt, 5, discount_rate, perpetual_growth, exit_multiple=recommended_exit_multiple)
        rev_5 = calculate_reverse_dcf(current_price, fcf, discount_rate, perpetual_growth, shares, dcf_cash, dcf_debt, 5, exit_multiple=recommended_exit_multiple)
        
        if res_5:
            # Use Perpetual as baseline for weighted average
            dcf_value = res_5["dcf_perpetual"]["fair_value"]
            # Apply WACC cap globally to the response
            discount_rate = res_5["discount_rate_applied"]
            
            dcf_5yr = {
                "result": res_5,
                "sensitivity": sens_5,
                "reverse_dcf": rev_5
            }
            
        # 10 Year Calculation 
        res_10 = calculate_dcf(fcf, eps_growth, discount_rate, perpetual_growth, shares, dcf_cash, dcf_debt, years=10, exit_multiple=recommended_exit_multiple, current_price=current_price)
        sens_10 = calculate_dcf_sensitivity(fcf, eps_growth, shares, dcf_cash, dcf_debt, 10, discount_rate, perpetual_growth, exit_multiple=recommended_exit_multiple)
        rev_10 = calculate_reverse_dcf(current_price, fcf, discount_rate, perpetual_growth, shares, dcf_cash, dcf_debt, 10, exit_multiple=recommended_exit_multiple)
        
        if res_10:
            dcf_10yr = {
                "result": res_10,
                "sensitivity": sens_10,
                "reverse_dcf": rev_10
            }
        # historical trends
        historical_trends = data.get("historical_trends", [])

        # v63: Stabilize Revenue Growth for Comparison (Avoid buggy TTM/quarterly picks)
        stable_rev_growth = data.get("revenue_growth")
        if historical_trends and len(historical_trends) >= 2:
            try:
                # trends might be [2022, 2023, 2024, 2025] or reversed. 
                # We extract the year number to sort correctly even with "(Est)" labels.
                def get_yr_num(h):
                    y_str = str(h.get("year", "0"))
                    nums = "".join(filter(str.isdigit, y_str))
                    return int(nums) if nums else 0
                
                # Sort descending: [2027 (Est), 2026 (Est), 2025, 2024...]
                sorted_trends = sorted(historical_trends, key=get_yr_num, reverse=True)
                
                # We only want REPORTED years for the 'historical' growth comparison (e.g. 2025 vs 2024)
                reported_revs = [h.get("revenue") for h in sorted_trends if h.get("revenue") and "(Est)" not in str(h.get("year"))]
                
                if len(reported_revs) >= 2:
                    curr_r = reported_revs[0]
                    prev_r = reported_revs[1]
                    if curr_r and prev_r and prev_r > 0:
                        stable_rev_growth = (curr_r - prev_r) / prev_r
            except:
                pass
        
        # Propagate stable revenue growth to both the profile and the scoring engine (v63 fix)
        data["revenue_growth"] = stable_rev_growth
        data["next_3y_rev_growth"] = stable_rev_growth
            
        # Stabilize Fair Value with Dynamic Financial Archetypes
        
        # Helper vars for Archetype Engine
        ind_lower = str(industry).lower() if industry else ""
        safe_sector = str(sector) if sector else "Default"
        
        m_rev_g = (data.get("next_3y_rev_growth") or stable_rev_growth or 0) * 100
        
        roic = data.get("roic") or 0
        if roic > 0 and roic <= 1.0:
            roic *= 100
            
        # Pasul 1: Filtre Sectoriale Stricte (Overrides)
        is_fin_special = False
        if safe_sector == "Financial Services":
            fin_keywords = ["bank", "insurance", "savings", "cooperative", "credit"]
            if any(k in ind_lower for k in fin_keywords):
                is_fin_special = True
                # Exclude Payment Networks (V, MA) which have very high ROIC from Traditional Financials
                if "credit" in ind_lower and (roic >= 20 or ticker.upper() in ["V", "MA", "PYPL", "AXP", "FI", "FIS", "GPN", "HOOD"]):
                    is_fin_special = False
                
        if is_fin_special:
            base_weights = {"dcf": 0.0, "relative": 0.45, "lynch": 0.45, "peg": 0.10}
            data["archetype"] = "Traditional Financials"
        elif safe_sector == "Real Estate":
            base_weights = {"relative": 0.40, "lynch": 0.30, "dcf": 0.20, "peg": 0.10}
            data["archetype"] = "Real Estate (REIT)"
        else:
            # Pasul 2: Motorul de Arhetipuri
            # 1. Distressed
            if targ_fwd_eps is not None and targ_fwd_eps <= 0:
                base_weights = {"dcf": 1.0, "relative": 0.0, "lynch": 0.0, "peg": 0.0}
                if not dcf_value:
                    base_weights = {"dcf": 0.0, "relative": 1.0, "lynch": 0.0, "peg": 0.0}
                data["archetype"] = "Distressed"
            # 2. Value / Capital Intensive
            elif roic < 10 or m_rev_g < 8:
                base_weights = {"relative": 0.40, "dcf": 0.40, "lynch": 0.10, "peg": 0.10}
                data["archetype"] = "Value / Capital Intensive"
            # 3. Hyper-Growth
            elif m_rev_g >= 20 and roic >= 10:
                base_weights = {"lynch": 0.35, "peg": 0.35, "dcf": 0.20, "relative": 0.10}
                data["archetype"] = "Hyper-Growth"
            # 4. Stable Moat
            else:
                base_weights = {"dcf": 0.35, "peg": 0.35, "lynch": 0.15, "relative": 0.15}
                data["archetype"] = "Stable Moat"

        # v316: Debug log for Archetype Engine transparency
        print(f"ARCHETYPE ENGINE | Company: {ticker.upper()} | Rev Growth: {m_rev_g:.2f}% | ROIC: {roic:.2f}% | Archetype: {data.get('archetype')} | Weights: dcf={base_weights.get('dcf',0)*100:.0f}% lynch={base_weights.get('lynch',0)*100:.0f}% peg={base_weights.get('peg',0)*100:.0f}% relative={base_weights.get('relative',0)*100:.0f}%")

        # Store archetype weights for frontend consumption
        data["archetype_weights"] = {
            "dcf": int(base_weights.get("dcf", 0) * 100),
            "lynch": int(base_weights.get("lynch", 0) * 100),
            "peg": int(base_weights.get("peg", 0) * 100),
            "relative": int(base_weights.get("relative", 0) * 100)
        }
 
        # Map methods to weight keys
        lynch_pe20_val = lynch_result.get("fair_value_pe_20")
        method_map = {
            "lynch": lynch_pe20_val,
            "peg": peg_value,
            "relative": relative_value,
            "dcf": dcf_value
        }
 
        # Calculate weighted average based on AVAILABLE methods
        total_weight = 0
        weighted_sum = 0
        for key, val in method_map.items():
            if val is not None and val > 0:
                w = base_weights.get(key, 0)
                weighted_sum += val * w
                total_weight += w
 
        if total_weight > 0:
            fair_value = weighted_sum / total_weight
            # Margin of Safety relative to PRICE is the standard for buy scores
            if current_price > 0:
                margin_of_safety = ((fair_value - current_price) / current_price) * 100
            else:
                margin_of_safety = 0
        else:
            fair_value = None
            margin_of_safety = None
            
        # Add bounds handling to avoid infinite or NaN
        def sanitize(val):
            if val is None:
                return val
            if isinstance(val, (int, float)):
                if not math.isfinite(val):
                    return None
                return round(val, 4)
            if isinstance(val, dict):
                return {k: sanitize(v) for k, v in val.items()}
            if isinstance(val, list):
                return [sanitize(v) for v in val]
            return val
            
        # Clean Median Rule for Peer Stats
        median_peer_pe = None
        mean_peer_pe = None
        median_peer_peg = None
        median_peer_pfcf = None
        mean_peer_pfcf = None
        median_peer_ps = None
        mean_peer_ps = None
        median_peer_pb = None
        mean_peer_pb = None
        median_peer_ev_ebitda = None
        mean_peer_ev_ebitda = None
        median_peer_ev_gp = None
        
        if peers_data:
            def get_clean_median(key):
                vals = []
                for p in peers_data:
                    v = p.get(key)
                    if v is not None and isinstance(v, (int, float)) and math.isfinite(v) and v > 0:
                        vals.append(float(v))
                if not vals:
                    return None
                return statistics.median(vals)
                
            # Compute Strict Forward Medians
            median_peer_pe = get_clean_median('pe_ratio')
            median_peer_ps = get_clean_median('ps_ratio')
            median_peer_ev_ebitda = get_clean_median('ev_to_ebitda')
            median_peer_pb = get_clean_median('price_to_book')
            median_peer_pfcf = get_clean_median('pfcf_ratio')
            
            valid_pegs = []
            valid_ev_gps = []
            for p in peers_data:
                if p.get('ticker') == ticker: continue
                val = p.get('peg_ratio')
                if val is not None and isinstance(val, (int, float)) and math.isfinite(val) and val > 0:
                    valid_pegs.append(float(val))
                
                # Calculate EV/GP
                p_rev_grow = p.get('revenue_growth') or 0
                if p_rev_grow > 1: p_rev_grow /= 100
                p_gm = p.get('gross_margins') or 0
                if p_gm > 1: p_gm /= 100
                p_rev = p.get('revenue') or 0
                p_fwd_rev = p_rev * (1 + p_rev_grow)
                p_fwd_gp = p_fwd_rev * p_gm
                p_ev = p.get('enterprise_value') or 0
                if p_fwd_gp > 0 and p_ev > 0:
                    valid_ev_gps.append(float(p_ev / p_fwd_gp))
                    
            if valid_pegs:
                median_peer_peg = statistics.median(valid_pegs)
                
            median_peer_ev_gp = statistics.median(valid_ev_gps) if valid_ev_gps else None
 
        # v285: PEG MUST use Adjusted (Non-GAAP) PE to match Non-GAAP Growth Estimates
        adj_pe = current_price / data.get("adjusted_eps") if data.get("adjusted_eps") and data.get("adjusted_eps") > 0 else None
 
        # 5. Build Formula Data for Transparency
        fair_value_sector_pe = None
        if lynch_result.get("fwd_eps") and median_peer_pe:
            fair_value_sector_pe = lynch_result.get("fwd_eps") * median_peer_pe
 
        def _format_dcf_payload(dcf_dict, exit_multiple_applied):
            if not dcf_dict or not dcf_dict.get("result"):
                return None
            res = dcf_dict["result"]
            sens = dcf_dict["sensitivity"]
            rev = dcf_dict["reverse_dcf"]
            
            # Shared fields across branches
            shared = {
                "fcf_projections": [sanitize(x) for x in res.get("fcf_years", [])],
                "pv_fcf_years": [sanitize(x) for x in res.get("pv_fcf_years", [])],
                "present_value_fcf_sum": sanitize(res.get("total_pv_of_fcfs")),
                "discount_rate": sanitize(res.get("discount_rate_applied")),
                "perpetual_growth_rate": perpetual_growth,
                "exit_multiple": exit_multiple_applied,
                "total_cash": sanitize(dcf_cash),
                "total_debt": sanitize(dcf_debt),
                "shares_outstanding": sanitize(shares)
            }

            def _fmt_branch(branch):
                if not branch: return None
                return {
                    "terminal_value": sanitize(branch.get("terminal_value")),
                    "present_value_terminal": sanitize(branch.get("pv_terminal_value")),
                    "fair_value_per_share": sanitize(branch.get("fair_value")),
                    "margin_of_safety_pct": sanitize(((branch.get("fair_value") - current_price) / current_price * 100)) if branch.get("fair_value") and current_price > 0 else 0,
                    **shared
                }

            per_branch = _fmt_branch(res.get("dcf_perpetual"))
            ext_branch = _fmt_branch(res.get("dcf_exit_multiple"))

            return {
                **shared,
                "dcf_perpetual": per_branch,
                "dcf_exit_multiple": ext_branch,
                "sensitivity_matrix": [
                    {
                        "discount_rate": sanitize(row["discount_rate"]),
                        "values": [{"perpetual_growth": sanitize(v["perpetual_growth"]), "fair_value": sanitize(v["fair_value"])} for v in row["values"]]
                    } for row in sens
                ] if sens else [],
                "reverse_dcf_growth": sanitize(rev) if rev is not None else None
            }

        # Derive implied 5Y EPS CAGR from Yahoo's PEG Ratio (5yr expected)
        # PEG = PE / Growth% => Growth% = PE / PEG => Growth (decimal) = PE / PEG / 100
        yahoo_peg_5yr = data.get("peg_ratio")
        forward_pe = data.get("forward_pe")

        implied_5y_growth = None
        if yahoo_peg_5yr and yahoo_peg_5yr > 0 and forward_pe and forward_pe > 0:
            implied_5y_growth = (forward_pe / yahoo_peg_5yr) / 100.0
            # Sanity: cap at 200% and floor at 0%
            if implied_5y_growth > 2.0: implied_5y_growth = 2.0
            if implied_5y_growth <= 0: implied_5y_growth = None

        formula_data = {
            "peter_lynch": {
                "current_price": sanitize(current_price),
                "trailing_eps": sanitize(data.get("trailing_eps")),
                "valuation_eps": sanitize(eps_for_valuation),
                "fwd_eps": sanitize(lynch_result.get("fwd_eps")),
                "eps_growth_estimated": sanitize(eps_growth_estimated),
                "eps_growth_5y_cagr": sanitize(implied_5y_growth),
                "eps_growth_period": lynch_period_label,
                "historic_pe": sanitize(pe_historic),
                "fwd_pe": sanitize(lynch_fwd_pe),
                "fair_value": sanitize(lynch_fair_value),
                "fair_value_pe_20": sanitize(lynch_pe20_val),
                "fair_value_sector_pe": sanitize(fair_value_sector_pe),
                "sector_pe": sanitize(median_peer_pe),
                "status": lynch_status,
                "margin_of_safety": sanitize(((lynch_fair_value - current_price) / lynch_fair_value * 100)) if lynch_fair_value and lynch_fair_value > 0 else None
            },
            "peg": {
                "current_pe": sanitize(current_pe),
                "eps_growth_estimated": sanitize(eps_growth_rate_peg),
                "eps_growth_5y_cagr": sanitize(implied_5y_growth),
                "eps_growth_period": peg_period_label,
                "current_peg": sanitize(company_peg) if company_peg > 0 else None,
                "industry_peg": sanitize(industry_peg) if industry_peg else None,
                "fair_value": sanitize(peg_value),
                "margin_of_safety": sanitize(((peg_value - current_price) / peg_value * 100)) if peg_value and peg_value > 0 else None
            },
            "dcf": {
                "fcf": sanitize(fcf),
                "eps_growth_applied": sanitize(eps_growth),
                "eps_growth_period": peg_period_label,
                "discount_rate": discount_rate,
                "perpetual_growth": perpetual_growth,
                "shares_outstanding": shares,
                "historic_buyback_rate": sanitize(data.get("historic_buyback_rate")),
                "intrinsic_value": sanitize(dcf_value),
                "margin_of_safety": sanitize(((dcf_value - current_price) / current_price * 100)) if dcf_value is not None and current_price > 0 else None,
                "current_price": sanitize(current_price),
                # Metadata for the modal (Flattened for compatibility)
                **( _format_dcf_payload(dcf_5yr or dcf_10yr, recommended_exit_multiple) or {} ),
                "5yr": _format_dcf_payload(dcf_5yr, recommended_exit_multiple) if dcf_5yr else None,
                "10yr": _format_dcf_payload(dcf_10yr, recommended_exit_multiple) if dcf_10yr else None
            },
            "relative": {
                "fair_value": sanitize(relative_value),
                "margin_of_safety": sanitize(((relative_value - current_price) / current_price * 100)) if relative_value is not None and current_price > 0 else None,
                "company_eps": sanitize(data.get("adjusted_eps") or data.get("trailing_eps")),
                "company_fwd_eps": sanitize(data.get("forward_eps")),
                "company_fcf_share": sanitize(data.get("fcf", 0) / shares if shares else 0),
                "company_sales_share": sanitize(data.get("revenue", 0) / shares if shares else 0),
                "company_book_share": sanitize(current_price / data.get("price_to_book") if data.get("price_to_book") and data.get("price_to_book") > 0 else 0),
                "company_ev_ebitda": sanitize(data.get("ev_to_ebitda") or ( ((current_price * shares) + data.get("total_debt", 0) - data.get("total_cash", 0)) / data.get("ebitda") if data.get("ebitda") and shares else None )),
                "company_trailing_pe": sanitize(pe_historic),
                "peers": [p.get("ticker", p) if isinstance(p, dict) else p for p in peers_data] if peers_data else [],
                "median_peer_pe": sanitize(median_peer_pe),
                "median_peer_pe": sanitize(median_peer_pe), # Forward P/E
                "median_peer_ps": sanitize(median_peer_ps), # Forward EV/Sales
                "median_peer_pb": sanitize(median_peer_pb),
                "median_peer_ev_ebitda": sanitize(median_peer_ev_ebitda), # Forward EV/EBITDA
                "median_peer_peg": sanitize(median_peer_peg),
                "market_pe_trailing": sanitize(market_data.get("trailing_pe")),
                "market_pe_forward": sanitize(market_data.get("forward_pe")),
                "sp500_pe": sanitize(market_data.get("trailing_pe")),
                "sp500_pfcf": 28.0,
                "sp500_ps": 2.8,
                "sp500_pb": 4.5,
                "sp500_ev_ebitda": 15.0,
                "sector": sector
            }
    }

        # Ensure we prioritize actual TTM multiple calculated using the most up-to-date price
        if current_price and data.get("trailing_eps") and data.get("trailing_eps") > 0:
            ttm_pe = current_price / data.get("trailing_eps")
        else:
            ttm_pe = data.get("pe_ratio") or 0
        
        data["trailing_pe"] = ttm_pe

        # FCF Trend Logic (Growing, Improving, Flat, Decreasing)
        fcf_vals = data.get("historical_data", {}).get("fcf", []) or [t.get("fcf") for t in data.get("historical_trends", []) if t.get("fcf") is not None]
        fcf_trend = "Flat"
        if len(fcf_vals) >= 2:
            # Newest is first if reversed by anchors. Let's stabilize it.
            # If anchors are newest-first, fcf_vals might be too. 
            # In SMCI diagnostic, it looked like oldest-first [..., 1.53B].
            current = fcf_vals[-1]
            prev = fcf_vals[-2]
            
            # RECOVERY LOGIC: Negative to Positive is a strong Growth signal
            if current > 0 and prev < 0:
                fcf_trend = "Growing" # Significant recovery
            elif current > prev * 1.05:
                fcf_trend = "Growing"
            elif current < prev * 0.95:
                fcf_trend = "Decreasing"
        elif data.get("historic_fcf_growth") is not None:
            g = data.get("historic_fcf_growth")
            if g > 0.02: fcf_trend = "Growing"
            elif g < -0.02: fcf_trend = "Decreasing"
        
        data["fcf_trend"] = fcf_trend

        # Financials placeholders (mapping from authoritative scraper data)
        data["nim"] = data.get("netInterestMargin") or 0
        data["cet1_ratio"] = data.get("cet1_ratio") or 0
        
        # PRIORITIZE CALCULATED RATIOS (ADBE/SMCI FIX)
        data["roe"] = data.get("roe") or 0
        data["roa"] = data.get("roa") or 0
        data["ebit_margin"] = (data.get("operating_margin") or data.get("ebit_margin") or 0)
        data["net_margin"] = (data.get("net_margin") or 0)
        
        data["bvps_growth"] = data.get("historic_bvps_growth") or 0
        data["next_3y_rev_growth"] = data.get("revenue_growth") or 0

        # Real Estate / REITs (mapping from scraper if available)
        # AFFO is often FCF for REITs if specific AFFO not parsed
        rev_val = data.get("revenue") or 0
        data["affo_margin"] = data.get("affo_margin") or (fcf/rev_val if fcf and rev_val > 0 else 0)
        data["affo_growth"] = data.get("historic_fcf_growth") or 0
        
        # Defensive Price to AFFO (avoid /0)
        p_affo = 0
        if fcf and shares and shares > 0 and (fcf/shares) != 0:
            p_affo = current_price / (fcf/shares)
        data["price_to_affo"] = p_affo
        
        # Defensive FCF Yield (avoid /0)
        mkt_cap_val = (current_price * shares) if (current_price and shares) else 0
        data["fcf_yield"] = (fcf / mkt_cap_val) if (fcf and mkt_cap_val > 0) else 0

        # RESTORE: Standard indicators for DEFAULT template (Respect Scraper Values)
        if not data.get("ebit_margin") or data["ebit_margin"] == 0:
            data["ebit_margin"] = (data.get("ebit", 0) / (rev_val or 1))
        
        # Only overwrite ps_ratio if scraper provided 0
        if not data.get("ps_ratio") or data["ps_ratio"] == 0:
            data["ps_ratio"] = current_price / (rev_val / (shares or 1)) if rev_val > 0 and shares > 0 else 0
        
        ebitda_val = data.get("ebitda")
        # Fix: current_price and shares are authoritative from earlier derivation
        mkt_cap_val = (shares or 0) * (current_price or 0)

        if ebitda_val and ebitda_val > 0:
            # Need dcf_debt/cash for EV
            debt_val = (data.get("total_debt") or 0)
            cash_val = (data.get("total_cash") or 0)
            ev_val = mkt_cap_val + debt_val - cash_val
            data["ev_to_ebitda"] = ev_val / ebitda_val
            data["debt_to_ebitda"] = debt_val / ebitda_val
        else:
            data["ev_to_ebitda"] = 0
            data["debt_to_ebitda"] = 0

        # 2Y Revenue CAGR for Scoring Module
        _rev_ests = data.get("rev_estimates") or []
        _est_growths = [float(t["growth"]) for t in _rev_ests if t.get("status") == "estimate" and t.get("growth") is not None]
        if len(_est_growths) >= 2:
            mult = (1 + _est_growths[0]) * (1 + _est_growths[1])
            data["rev_cagr_2y"] = (mult ** 0.5 - 1) if mult >= 0 else ((_est_growths[0] + _est_growths[1]) / 2.0)
        elif len(_est_growths) == 1:
            data["rev_cagr_2y"] = _est_growths[0]
        else:
            data["rev_cagr_2y"] = stable_rev_growth or 0.08        # Pass safety values to scoring
        safe_mos = margin_of_safety if margin_of_safety is not None else 0
        safe_median_peg = median_peer_peg if median_peer_peg is not None else 0
        
        from models.scoring import calculate_health_score, calculate_scoring_reform
        
        valuation_data_for_scoring = {
            "margin_of_safety": safe_mos,
            "sector_median_peg": safe_median_peg,
            "sector_median_pe": median_peer_pe if median_peer_pe else 0,
            "sector_median_ps": median_peer_ps if median_peer_ps else 0,
            "sector_median_ev_ebitda": median_peer_ev_ebitda if median_peer_ev_ebitda else 0,
            "sector_median_pb": median_peer_pb if median_peer_pb else 0,
            "historic_pe": pe_historic if pe_historic else 0,
            "market_cap": data.get("shares_outstanding", 0) * current_price if data.get("shares_outstanding") and current_price else 0.0
        }
        
        def calculate_scenario_score(scenario_type):
            metrics_copy = data.copy()
            eps_ests = metrics_copy.get("eps_estimates", [])
            rev_ests = metrics_copy.get("rev_estimates", [])
            
            if scenario_type == "base":
                eps_key = "avg"
                rev_key = "avg"
            elif scenario_type == "bear":
                eps_key = "low"
                rev_key = "low"
            elif scenario_type == "bull":
                eps_key = "high"
                rev_key = "high"
                
            
            # Find the first estimate (which represents the current FY / FY1)
            fy1_eps_est = next((e for e in eps_ests if e.get("status") == "estimate"), None)
            fy1_rev_est = next((e for e in rev_ests if e.get("status") == "estimate"), None)
            
            if fy1_eps_est and fy1_eps_est.get(eps_key):
                eps_val = fy1_eps_est[eps_key]
                if eps_val != 0:
                    metrics_copy["forward_pe"] = current_price / eps_val
                    metrics_copy["fwd_pe"] = metrics_copy["forward_pe"]
                
            if fy1_rev_est and fy1_rev_est.get(rev_key) and fy1_rev_est.get(rev_key) > 0:
                rev_val = fy1_rev_est[rev_key]
                metrics_copy["forward_revenue"] = rev_val
                if shares and shares > 0:
                    metrics_copy["fwd_ps"] = current_price / (rev_val / shares)
                    metrics_copy["ps_ratio"] = metrics_copy["fwd_ps"]
                    
                base_rev = fy1_rev_est.get("avg")
                if base_rev and base_rev > 0:
                    ratio = rev_val / base_rev
                    base_ev_ebitda = data.get("ev_to_ebitda") or 0
                    if base_ev_ebitda > 0:
                        metrics_copy["forward_ev_ebitda"] = base_ev_ebitda / ratio
                        metrics_copy["ev_to_ebitda"] = metrics_copy["forward_ev_ebitda"]
            
            ttm_rev = data.get("revenue") or data.get("total_revenue")
            if ttm_rev and ttm_rev > 0 and fy1_rev_est and fy1_rev_est.get(rev_key):
                metrics_copy["forward_revenue_growth"] = (fy1_rev_est[rev_key] - ttm_rev) / ttm_rev
                metrics_copy["fwd_rev_growth"] = metrics_copy["forward_revenue_growth"]
            
            ttm_eps = data.get("trailing_eps") or data.get("adjusted_eps")
            if ttm_eps and ttm_eps > 0 and fy1_eps_est and fy1_eps_est.get(eps_key):
                metrics_copy["eps_growth"] = (fy1_eps_est[eps_key] - ttm_eps) / ttm_eps
                
            return calculate_scoring_reform(valuation_data_for_scoring, metrics_copy)

        scoring_base = calculate_scenario_score("base")
        scoring_bear = calculate_scenario_score("bear")
        scoring_bull = calculate_scenario_score("bull")
        
        health_results = calculate_health_score(data)
        health_score_total = health_results.get("total")
        health_breakdown = health_results.get("breakdown")
        beneish_data = health_results.get("beneish")
        
        # Fallback to base score for the old keys to prevent breaking changes
        good_to_buy_total = scoring_base.get("good_to_buy_total")
        buy_breakdown = scoring_base.get("buy_breakdown")
        
        # Piotroski F-Score & Rule of 40
        from models.scoring import calculate_piotroski_score, calculate_rule_of_40
        piotroski_result = calculate_piotroski_score(data)
        rule_of_40_result = calculate_rule_of_40(data)

        # 7. Algorithmic Insights Generation
        all_breakdowns = health_breakdown + buy_breakdown
        top_strengths = []
        risk_factors = []
        
        if all_breakdowns:
            # Strengths: items with max points
            max_point_items = [b for b in all_breakdowns if b.get("points_awarded") == b.get("max_points") and b.get("max_points", 0) > 0]
            # Sort by highest max_points just to show the most impactful ones first
            max_point_items.sort(key=lambda x: x.get("max_points", 0), reverse=True)
            top_strengths = max_point_items[:3]
            
            # Risks: items with 0 points
            zero_point_items = [b for b in all_breakdowns if b.get("points_awarded") == 0]
            if zero_point_items:
                risk_factors = zero_point_items[:3]
            else:
                # Fallback: lowest partial points if no 0s
                all_sorted = sorted(all_breakdowns, key=lambda x: x.get("points_awarded", 100))
                risk_factors = all_sorted[:2]

        response_data = {
            "ticker": ticker_upper,
            "name": data.get("name", "Unknown"),
            "current_price": float(current_price or 0.0),
            "fair_value": sanitize(fair_value),
            "margin_of_safety": sanitize(margin_of_safety),
            "dcf_value": sanitize(dcf_value),
            "relative_value": sanitize(relative_value),
            "lynch_fwd_pe": sanitize(lynch_fwd_pe),
            "lynch_fair_value": sanitize(lynch_fair_value),
            "lynch_status": lynch_status,
            "peg_value": sanitize(peg_value),
            "recommended_exit_multiple": sanitize(recommended_exit_multiple),
            "eps_estimates": sanitize(data.get("eps_estimates", [])),
            "rev_estimates": sanitize(data.get("rev_estimates", [])),
            "company_profile": {
                "industry": data.get("industry") or "N/A",
                "sector": data.get("sector") or "N/A",
                "market_cap": sanitize(data.get("shares_outstanding", 0) * current_price if data.get("shares_outstanding") and current_price else 0.0),
                "adjusted_eps": sanitize(data.get("adjusted_eps")),
                "fwd_eps": sanitize(next((e.get("avg") for e in data.get("eps_estimates", []) if e.get("status") == "estimate"), None)),
                "peg_eps_type": data.get("peg_eps_type"),
                # Force strict 2-year PEG based on Forward PE and 2Y EPS Growth instead of Yahoo 5y PEG. No fallbacks.
                "peg_ratio": sanitize(
                    data.get("fwd_pe") / (data.get("eps_growth") * 100.0) if data.get("fwd_pe") and data.get("eps_growth") and data.get("eps_growth") > 0 
                    else None
                ),
                "ps_ratio": sanitize(data.get("ps_ratio")),
                "price_to_book": sanitize(data.get("price_to_book")),
                "fwd_ps": sanitize(data.get("fwd_ps")),
                "pfcf_ratio": sanitize(data.get("pfcf_ratio")),
                "current_pe": sanitize(current_pe),
                "gross_margins": sanitize(data.get("gross_margins")),
                "quick_ratio": sanitize(data.get("quick_ratio")),
                "ebitda_margins": sanitize(data.get("ebitda_margins")),
                "total_revenue": sanitize(data.get("total_revenue")),
                "enterprise_value": sanitize(data.get("enterprise_value")),
                "ev_to_ebitda": sanitize(data.get("ev_to_ebitda")),
                "forward_revenue": sanitize(data.get("forward_revenue")) or sanitize(next((e.get("avg") for e in data.get("rev_estimates", []) if e.get("status") == "estimate"), None)),
                "trailing_pe": sanitize(ttm_pe),
                "trailing_eps": sanitize(data.get("trailing_eps")),
                "historic_eps_growth": sanitize(data.get("historic_eps_growth")),
                "historic_fcf_growth": sanitize(data.get("historic_fcf_growth")),
                "debt_to_equity": sanitize(data.get("debt_to_equity")),
                "operating_margin": sanitize(data.get("operating_margin")),
                "ebit_margin": sanitize(data.get("ebit_margin")),
                "net_margin": sanitize(data.get("net_margin")),
                "revenue_growth": sanitize(next((float(e.get("growth")) for e in data.get("rev_estimates", []) if e.get("status") == "estimate" and e.get("growth") is not None), stable_rev_growth)),
                "earnings_growth": sanitize(next((float(e.get("growth")) for e in data.get("eps_estimates", []) if e.get("status") == "estimate" and e.get("growth") is not None), consensus_growth)),
                "rev_cagr_2y": sanitize(data.get("rev_cagr_2y")),
                "business_summary": data.get("business_summary"),
                "sector_median_pe": sanitize(median_peer_pe),
                "sector_median_peg": sanitize(median_peer_peg),
                "sector_median_ev_gp": sanitize(median_peer_ev_gp),
                # Newly added fields (v59 Fix)
                "next_earnings_date": data.get("next_earnings_date") or "N/A",
                "historic_pe": sanitize(pe_historic),
                "insider_ownership": sanitize(data.get("insider_ownership")),
                "shares_outstanding": sanitize(data.get("shares_outstanding")),
                "buyback_rate": sanitize(data.get("buyback_rate") if data.get("buyback_rate") is not None else data.get("historic_buyback_rate")),
                "dividend_yield": sanitize(data.get("dividend_yield")),
                "payout_ratio": sanitize(data.get("payout_ratio")),
                "dividend_streak": data.get("dividend_streak"),
                "dividend_cagr_5y": sanitize(data.get("dividend_cagr_5y")),
                "fwd_pe": sanitize(data.get("fwd_pe")),
                "forward_pe_custom": sanitize(data.get("forward_pe_custom")),
                "cagr_5y_custom": sanitize(data.get("cagr_5y_custom")),
                "peg_custom": sanitize(data.get("peg_custom")),
                "forward_ev_sales": sanitize(data.get("forward_ev_sales")),
                "forward_ev_ebitda": sanitize(data.get("forward_ev_ebitda")),
                "ps_forward_custom": sanitize(data.get("ps_forward_custom")),
                "fcf_margin_custom": sanitize(data.get("fcf_margin_custom")),
                "pfcf_forward_custom": sanitize(data.get("pfcf_forward_custom")),
                "competitors": [p.get("ticker") for p in peers_data] if peers_data else [],
                "competitor_metrics": [{
                    "ticker": p.get("ticker"),
                    "name": p.get("name"),
                    "price": sanitize(p.get("price")),
                    "pe_ratio": sanitize(p.get("pe_ratio")),
                    "pe_non_gaap": sanitize(p.get("pe_non_gaap")),
                    "peg_ratio": sanitize(p.get("peg_ratio")),
                    "peg_eps_type": p.get("peg_eps_type"),
                    "pfcf_ratio": sanitize(p.get("pfcf_ratio")),
                    "ps_ratio": sanitize(p.get("ps_ratio")),
                    "price_to_book": sanitize(p.get("price_to_book")),
                    "ev_to_ebitda": sanitize(p.get("ev_to_ebitda")),
                    "market_cap": sanitize(p.get("market_cap")),
                    "enterprise_value": sanitize(p.get("enterprise_value")),
                    "gross_margins": sanitize(p.get("gross_margins")),
                    "eps": sanitize(p.get("eps")),
                    "revenue": sanitize(p.get("revenue")),
                    "fcf": sanitize(p.get("fcf")),
                    "operating_margin": sanitize(p.get("operating_margin")),
                    "revenue_growth": sanitize(p.get("revenue_growth")),
                    "earnings_growth": sanitize(p.get("earnings_growth")),
                    "forward_pe": sanitize(p.get("forward_pe_custom") if p.get("forward_pe_custom") is not None else p.get("forward_pe")),
                    "forward_ev_sales": sanitize(p.get("forward_ev_sales")),
                    "forward_ev_ebitda": sanitize(p.get("forward_ev_ebitda")),
                    "avg_2y_eps_growth": sanitize(p.get("avg_2y_eps_growth")),
                    "forward_peg": sanitize(p.get("forward_peg")),
                    "forward_pe_custom": sanitize(p.get("forward_pe_custom")),
                    "cagr_5y_custom": sanitize(p.get("cagr_5y_custom")),
                    "peg_custom": sanitize(p.get("peg_custom")),
                    "ps_forward_custom": sanitize(p.get("ps_forward_custom")),
                    "fcf_margin_custom": sanitize(p.get("fcf_margin_custom")),
                    "pfcf_forward_custom": sanitize(p.get("pfcf_forward_custom"))
                } for p in peers_data] if peers_data else []
            },
            "revenue": sanitize(data.get("revenue")),
            "ebitda": sanitize(data.get("ebitda")),
            "total_cash": sanitize(data.get("total_cash")),
            "total_debt": sanitize(data.get("total_debt")),
            "price_to_book": sanitize(data.get("price_to_book")),
            "dividend_rate": sanitize(data.get("dividend_rate")),
            "historical_trends": data.get("historical_trends"),
            "historical_anchors": historical_anchors,
            "company_overview_synthesis": data.get("company_overview_synthesis"),
            "health_score_total": health_score_total,
            "health_breakdown": health_breakdown,
            "health_score": { "beneish": beneish_data },
            "good_to_buy_total": good_to_buy_total,
            "buy_breakdown": buy_breakdown,
            "scoring_results": {"base": scoring_base, "bear": scoring_bear, "bull": scoring_bull},
            "piotroski": piotroski_result,
            "rule_of_40": rule_of_40_result,
            "formula_data": formula_data,
            "recommended_exit_multiple": recommended_exit_multiple,
            "dcf_assumptions": {
                "recommended_exit_multiple": recommended_exit_multiple
            },
            "historical_data": data.get("historical_data"),
            "algorithmic_insights": {
                "top_strengths": top_strengths,
                "risk_factors": risk_factors
            },
            "red_flags": data.get("red_flags", []),
            "overrides": ticker_overrides,
            "archetype": data.get("archetype"),
            "archetype_weights": data.get("archetype_weights"),
            "ownership": data.get("ownership")
        }
    except Exception as e:
        import traceback
        error_msg = f"VALUATION CRASH for {ticker}: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": True, "detail": "An internal error occurred during valuation."}
        )

    # 3. Save to memory cache (v38: Fix for slowness and desync)
    valuation_cache[cache_key] = response_data
    
    # 3.5 Save to persistent KV cache so that `get_competitors_data` can intercept and sync parity
    try:
        from utils.kv import kv_set
        if not skip_peers and not fast_mode:
            kv_set(f"val_data_v30_{ticker_upper}", response_data, ex=86400)
        elif skip_peers and not fast_mode:
            kv_set(f"val_data_v30_skip_{ticker_upper}", response_data, ex=86400)
    except Exception as e:
        print(f"Failed to cache main profile to KV for {ticker_upper}: {e}")

    # LIQUID DEFENSE: Deep clean before sending
    return deep_clean_data(response_data)

from concurrent.futures import ThreadPoolExecutor

@app.post("/api/batch-valuation")
def get_batch_valuation(req: WatchlistRequest):
    tickers = req.tickers
    results = []
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        # User requested reliable data: We must use fast_mode=False for the watchlist. 
        # Skipping DataFrames completely destroys the Health and Buy scores (e.g. Health 92 -> 62)
        # because metrics like buyback_rate and historic_eps_growth become None.
        # Likewise, skipping peers breaks the Fair Value and Buy Score algorithms by removing the relative valuation anchors.
        futures = {executor.submit(get_valuation, t.upper(), None, False, False): t for t in tickers}
        for future in futures:
            try:
                res = future.result()
                if res and not res.get("error"):
                    results.append(res)
            except Exception as e:
                ticker = futures[future]
                print(f"Batch Error for {ticker}: {e}")
                
    return results

@app.get("/api/valuation/{ticker}/synthesis")
def get_synthesis(ticker: str, response: Response):
    # Set Vercel Edge Cache headers for synthesis (Cache 1hr, stale up to 24hr)
    response.headers["Cache-Control"] = "public, s-maxage=3600, stale-while-revalidate=86400"
    
    ticker_upper = ticker.upper()
    try:
        # 1. Check if we have cached info from get_company_data
        info = _company_info_cache.get(ticker_upper)
        if not info:
            # 2. Dynamic fallback if info is not cached (e.g. direct synthesis request or container recycle)
            import yfinance as yf
            stock = yf.Ticker(ticker_upper)
            info = stock.info
            if info:
                _company_info_cache[ticker_upper] = info
                
        if not info:
            raise HTTPException(status_code=404, detail="Company profile info not found")
            
        # 3. Call get_company_synthesis with run_ai=True to invoke Gemini API
        synthesis = get_company_synthesis(ticker_upper, info, run_ai=True)
        return {"ticker": ticker_upper, "company_overview_synthesis": synthesis}
        
    except Exception as e:
        import traceback
        print(f"Error in synthesis endpoint for {ticker_upper}: {e}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": True, "detail": "Synthesis failed due to an internal server error."}
        )

@app.get("/api/firebase-config")
def get_firebase_config():
    # Firebase config hidden from frontend code
    return JSONResponse(content={
        "apiKey": os.environ.get("FIREBASE_API_KEY", "AIzaSyBqnECMrco2mrqLEyo-mTMdIYbaku-N0f4"),
        "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", "babi-calculator-inatorul.firebaseapp.com"),
        "projectId": os.environ.get("FIREBASE_PROJECT_ID", "babi-calculator-inatorul"),
        "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", "babi-calculator-inatorul.firebasestorage.app"),
        "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "332002590695"),
        "appId": os.environ.get("FIREBASE_APP_ID", "1:332002590695:web:ffaebc5eb3b62548cb8742")
    })

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)


@app.get("/api/live-price/{ticker}")
def get_live_price(ticker: str):
    import yfinance as yf
    try:
        stock = yf.Ticker(ticker)
        # Using fast_info for speed if available, or fallback to info
        price = None

        # Try fast_info first (faster, less rate-limited)
        try:
            if hasattr(stock, 'fast_info') and 'lastPrice' in stock.fast_info:
                price = stock.fast_info['lastPrice']
        except Exception:
            pass

        if not price:
            info = stock.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")

        return {"ticker": ticker, "price": price}
    except Exception as e:
        return {"error": str(e)}
