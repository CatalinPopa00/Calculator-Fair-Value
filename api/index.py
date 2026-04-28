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

from scraper.yahoo import get_company_data, get_competitors_data, get_market_averages, search_companies, get_analyst_data, get_risk_free_rate
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
CACHE_VERSION = "v269"
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

# KV functions moved to .utils.kv

@app.get("/api/watchlist")
def get_watchlist():
    try:
        data = kv_get("watchlist") or []
        # Robust Recovery: Merge any tickers found in overrides
        all_overrides = _load_overrides()
        if all_overrides:
            override_tickers = [t.upper() for t in all_overrides.keys()]
            data = list(set(data + override_tickers))
        
        if not data and os.path.exists(WATCHLIST_FILE):
            try:
                with open(WATCHLIST_FILE, "r") as f:
                    data = json.load(f)
            except:
                pass
        return list(set([t.upper() for t in data]))
    except Exception as e:
        # v37 Fix: If database errors, do NOT return []. Return 500.
        raise HTTPException(status_code=500, detail=f"Database unreachable: {str(e)}")

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
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=500, detail=str(e))


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
def get_valuation(ticker: str, response: Response, wacc: float = None, fast_mode: bool = False, skip_peers: bool = False):
    # Set Vercel Edge Cache headers for pseudo-ISR (Cache 1hr, stale up to 24hr)
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
        if fast_mode or skip_peers:
            full_mode_key = f"valuation_{ticker.upper()}_False_False_{CACHE_VERSION}_{norm_wacc}"
            if full_mode_key in valuation_cache:
                return valuation_cache[full_mode_key]

        # 2. Local Memory Cache check for the specific requested mode
        if cache_key in valuation_cache:
            return valuation_cache[cache_key]

        # v41: THE PARALLEL BLITZ
        # Run main scraping and peer fetching simultaneously to cut wait time in half.
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        # 1. Start main scraper
        main_task = executor.submit(get_company_data, ticker, fast_mode=fast_mode)
        
        # 2. Start peer scraper (pass None for strings, yahoo.py handles ticker-based resolution)
        peer_task = None
        if not skip_peers:
            peer_task = executor.submit(get_competitors_data, ticker, None, None, limit=3)
        
        # Wait for main data first
        data = main_task.result() or {}
        
        # --- DYNAMIC FX CURRENCY CONVERSION TO USD ---
        price_currency = data.get("currency", "USD")
        fin_currency = data.get("financial_currency", "USD")
        
        price_fx = get_usd_fx_rate(price_currency)
        fin_fx = get_usd_fx_rate(fin_currency)
        
        # Convert price-dependent metrics
        if price_fx != 1.0:
            if data.get("current_price"): data["current_price"] = data["current_price"] * price_fx
            
        # Convert financial-dependent metrics
        if fin_fx != 1.0:
            for key in ["adjusted_eps", "trailing_eps", "fwd_eps", "fcf", "total_cash", "total_debt", "revenue", "ebitda"]:
                if data.get(key) is not None:
                    data[key] = data[key] * fin_fx
            
            # Convert multi-year eps estimates
            if data.get("eps_estimates"):
                for est in data["eps_estimates"]:
                    if est.get("avg") is not None:
                        est["avg"] = est["avg"] * fin_fx
            
            # Convert historical data
            if data.get("historical_data"):
                for h_key in ["revenue", "eps", "diluted_eps", "fcf"]:
                    if data["historical_data"].get(h_key):
                        data["historical_data"][h_key] = [v * fin_fx if v is not None else None for v in data["historical_data"][h_key]]
        
        # Get peer data
        peers_data = []
        if peer_task:
            try:
                # v63: Increased timeout to 10s to handle slow Yahoo parallel fetches
                peers_data = peer_task.result(timeout=10) or []
            except Exception as e:
                print(f"DEBUG: Parallel peer fetch failed: {e}")
                peers_data = []
                
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
        eps_base = eps_for_valuation or 0
        current_pe = current_price / eps_base if eps_base > 0 else 0
        
        # Fallback logic handled by consensus_growth
        eps_growth_rate_peg = consensus_growth
        
        peg_period_label = data.get("eps_growth_period") or "2Y EPS CAGR"
        company_peg = current_pe / (eps_growth_rate_peg * 100) if eps_growth_rate_peg > 0 else 0
        
        # Calculate Industry PEG from peers ONLY (v261: Remove target company to prevent circular bias)
        valid_pegs = []
        
        if peers_data:
            for p in peers_data:
                v = p.get('peg_ratio')
                if v is not None and isinstance(v, (int, float)) and math.isfinite(v) and v > 0:
                    valid_pegs.append(float(v))
        
        # v61: Improved industry PEG fallback to 1.25 if no peer data is available
        industry_peg = statistics.median(valid_pegs) if valid_pegs else 1.25
        peg_value = calculate_peg_fair_value(current_price, company_peg, industry_peg)
        
        # Relative Valuation (P/E Based currently)
        relative_value = calculate_relative_valuation(ticker, data, peers_data)
        
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
        res_5 = calculate_dcf(fcf, eps_growth, discount_rate, perpetual_growth, shares, dcf_cash, dcf_debt, years=5, exit_multiple=recommended_exit_multiple)
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
        res_10 = calculate_dcf(fcf, eps_growth, discount_rate, perpetual_growth, shares, dcf_cash, dcf_debt, years=10, exit_multiple=recommended_exit_multiple)
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
            
        # Stabilize Fair Value with Sector-Aware Weighting
        # Define base sector weights using the pre-assigned sector variable
        if sector == "Financial Services":
            base_weights = {"lynch": 0.45, "relative": 0.45, "peg": 0.10, "dcf": 0.0}
        elif sector == "Real Estate":
            base_weights = {"lynch": 0.30, "relative": 0.40, "peg": 0.10, "dcf": 0.20}
        else:
            base_weights = {"lynch": 0.25, "relative": 0.25, "peg": 0.25, "dcf": 0.25}
 
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
            if val is None or not isinstance(val, (int, float)):
                return val
            if not math.isfinite(val):
                return None
            return round(val, 4)
            
        # Calculate Peer PE stats safely
        median_peer_pe = None
        mean_peer_pe = None
        median_peer_peg = None
        if peers_data:
            valid_pes = []
            for p in peers_data:
                val = p.get('pe_ratio')
                if val is not None and isinstance(val, (int, float)) and math.isfinite(val) and val > 0:
                    valid_pes.append(float(val))
            
            if valid_pes:
                median_peer_pe = statistics.median(valid_pes)
                mean_peer_pe = sum(valid_pes) / len(valid_pes)
                
            valid_pegs = []
            for p in peers_data:
                if p.get('ticker') == ticker: continue
                val = p.get('peg_ratio')
                if val is not None and isinstance(val, (int, float)) and math.isfinite(val):
                    valid_pegs.append(float(val))
            
            if valid_pegs:
                median_peer_peg = statistics.median(valid_pegs)
 
        # v285: PEG MUST use Adjusted (Non-GAAP) PE to match Non-GAAP Growth Estimates
        adj_pe = current_price / data.get("adjusted_eps") if data.get("adjusted_eps") and data.get("adjusted_eps") > 0 else None
        current_pe = adj_pe
 
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

        formula_data = {
            "peter_lynch": {
                "current_price": sanitize(current_price),
                "trailing_eps": sanitize(data.get("trailing_eps")),
                "fwd_eps": sanitize(lynch_result.get("fwd_eps")),
                "eps_growth_estimated": sanitize(eps_growth_estimated),
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
                "eps_growth_period": peg_period_label,
                "current_peg": sanitize(company_peg) if company_peg > 0 else None,
                "industry_peg": sanitize(industry_peg) if industry_peg else 1.25,
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
                "company_eps": sanitize(data.get("historical_data", {}).get("diluted_eps", [data.get("trailing_eps")])[-1]),
                "company_trailing_pe": sanitize(pe_historic),
                "peers": [p.get("ticker", p) if isinstance(p, dict) else p for p in peers_data] if peers_data else [],
                "median_peer_pe": sanitize(median_peer_pe),
                "median_peer_peg": sanitize(median_peer_peg),
                "mean_peer_pe": sanitize(mean_peer_pe),
                "market_pe_trailing": sanitize(market_data.get("trailing_pe")),
                "market_pe_forward": sanitize(market_data.get("forward_pe"))
            }
    }

        # USER-DRIVEN DATA MAPPING: TRAILING PE ONLY (FORBIDDEN FORWARD PE)
        # Ensure we prioritize actual TTM multiple
        ttm_pe = data.get("pe_ratio")
        if not ttm_pe or ttm_pe <= 0:
            if current_price and data.get("trailing_eps") and data.get("trailing_eps") > 0:
                ttm_pe = current_price / data.get("trailing_eps")
            else:
                ttm_pe = 0
        
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
        data["ebit_margin"] = (data.get("operating_margin") or data.get("ebit_margin") or 0) * 100
        data["net_margin"] = (data.get("net_margin") or 0) * 100
        
        data["bvps_growth"] = data.get("historic_bvps_growth") or 0
        data["next_3y_rev_growth"] = data.get("revenue_growth") or 0

        # Real Estate / REITs (mapping from scraper if available)
        # AFFO is often FCF for REITs if specific AFFO not parsed
        rev_val = data.get("revenue") or 0
        data["affo_margin"] = data.get("affo_margin") or (fcf/rev_val*100 if fcf and rev_val > 0 else 0)
        data["affo_growth"] = data.get("historic_fcf_growth") or 0
        
        # Defensive Price to AFFO (avoid /0)
        p_affo = 0
        if fcf and shares and shares > 0 and (fcf/shares) != 0:
            p_affo = current_price / (fcf/shares)
        data["price_to_affo"] = p_affo
        
        # Defensive FCF Yield (avoid /0)
        mkt_cap_val = (current_price * shares) if (current_price and shares) else 0
        data["fcf_yield"] = (fcf / mkt_cap_val * 100) if (fcf and mkt_cap_val > 0) else 0

        # RESTORE: Standard indicators for DEFAULT template (Respect Scraper Values)
        if not data.get("ebit_margin") or data["ebit_margin"] == 0:
            data["ebit_margin"] = (data.get("ebit", 0) / (rev_val or 1)) * 100
        
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

        # Pass safety values to scoring
        safe_mos = margin_of_safety if margin_of_safety is not None else 0
        safe_median_peg = median_peer_peg if median_peer_peg is not None else 0
        
        scoring_results = calculate_scoring_reform({"margin_of_safety": safe_mos, "sector_median_peg": safe_median_peg}, data)
        
        health_score_total = scoring_results.get("health_score_total")
        health_breakdown = scoring_results.get("health_breakdown")
        
        good_to_buy_total = scoring_results.get("good_to_buy_total")
        buy_breakdown = scoring_results.get("buy_breakdown")

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
            "company_profile": {
                "industry": data.get("industry") or "N/A",
                "sector": data.get("sector") or "N/A",
                "market_cap": sanitize(data.get("shares_outstanding", 0) * current_price if data.get("shares_outstanding") and current_price else 0.0),
                "adjusted_eps": sanitize(data.get("adjusted_eps")),
                "fwd_eps": sanitize(next((e.get("avg") for e in data.get("eps_estimates", []) if e.get("status") == "estimate"), None)),
                "peg_ratio": sanitize(company_peg if company_peg > 0 else None),
                "ps_ratio": sanitize(data.get("ps_ratio")),
                "fwd_ps": sanitize(data.get("fwd_ps")),
                "pfcf_ratio": sanitize((data.get("shares_outstanding", 0) * current_price) / data.get("fcf")) if data.get("shares_outstanding") and current_price and data.get("fcf") else None,
                "current_pe": sanitize(current_pe),
                "trailing_pe": sanitize(ttm_pe),
                "trailing_eps": sanitize(data.get("trailing_eps")),
                "historic_eps_growth": sanitize(data.get("historic_eps_growth")),
                "historic_fcf_growth": sanitize(data.get("historic_fcf_growth")),
                "debt_to_equity": sanitize(data.get("debt_to_equity")),
                "operating_margin": sanitize(data.get("operating_margin")),
                "net_margin": sanitize(data.get("net_margin")),
                "revenue_growth": sanitize(stable_rev_growth), # Use calculated 1Y historical growth for stability
                "earnings_growth": sanitize(consensus_growth), # Use Consensus/Nasdaq CAGRs for comparison instead of buggy Yahoo TTM
                "business_summary": data.get("business_summary"),
                "sector_median_pe": sanitize(median_peer_pe),
                "sector_median_peg": sanitize(median_peer_peg),
                # Newly added fields (v59 Fix)
                "next_earnings_date": data.get("next_earnings_date") or "N/A",
                "historic_pe": sanitize(data.get("pe_historic")),
                "insider_ownership": sanitize(data.get("insider_ownership")),
                "shares_outstanding": sanitize(data.get("shares_outstanding")),
                "buyback_rate": sanitize(data.get("historic_buyback_rate")),
                "dividend_yield": sanitize(data.get("dividend_yield")),
                "payout_ratio": sanitize(data.get("payout_ratio")),
                "dividend_streak": data.get("dividend_streak"),
                "dividend_cagr_5y": sanitize(data.get("dividend_cagr_5y")),
                "fwd_pe": sanitize(data.get("fwd_pe")),
                "competitors": [p.get("ticker") for p in peers_data] if peers_data else [],
                "competitor_metrics": [{
                    "ticker": p.get("ticker"),
                    "name": p.get("name"),
                    "price": sanitize(p.get("price")),
                    "pe_ratio": sanitize(p.get("pe_ratio")),
                    "market_cap": sanitize(p.get("market_cap")),
                    "eps": sanitize(p.get("eps")),
                    "operating_margin": sanitize(p.get("operating_margin")),
                    "revenue_growth": sanitize(p.get("revenue_growth")),
                    "earnings_growth": sanitize(p.get("earnings_growth"))
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
            "good_to_buy_total": good_to_buy_total,
            "buy_breakdown": buy_breakdown,
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
            "overrides": ticker_overrides
        }
    except Exception as e:
        import traceback
        error_msg = f"VALUATION CRASH for {ticker}: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": True, "detail": error_msg, "traceback": traceback.format_exc()}
        )

    # 3. Save to memory cache (v38: Fix for slowness and desync)
    valuation_cache[cache_key] = response_data

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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
