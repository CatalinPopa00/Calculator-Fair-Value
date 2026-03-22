from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cachetools import TTLCache
import uvicorn
import math
import statistics

import urllib.request
import urllib.parse
import json

import os
import requests
from .scraper.yahoo import get_company_data, get_competitors_data, get_market_averages, search_companies, get_analyst_data, get_risk_free_rate
from .models.valuation import (
    calculate_peter_lynch, 
    calculate_peg_fair_value, 
    calculate_dcf, 
    calculate_relative_valuation,
    calculate_dcf_sensitivity,
    calculate_reverse_dcf
)
from .models.scoring import calculate_health_score, calculate_buy_score

app = FastAPI(title="Fair Value Calculator API")

# Cache for search results (30 mins TTL)
search_cache = TTLCache(maxsize=500, ttl=30 * 60)
# Valuation cache (1 hour TTL for active development/accuracy)
valuation_cache = TTLCache(maxsize=1000, ttl=60 * 60)
CACHE_VERSION = "v3" # Incrementing version forces invalidation of old logic results

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

class ValuationResponse(BaseModel):
    ticker: str
    name: str
    current_price: float
    fair_value: float | None
    margin_of_safety: float | None
    dcf_value: float | None
    relative_value: float | None
    lynch_fwd_pe: float | None
    lynch_fair_value: float | None
    lynch_status: str | None
    peg_value: float | None
    company_profile: dict | None = None
    historical_trends: list | None = None
    formula_data: dict
    health_score: int | str | None = None
    health_breakdown: list | None = None
    buy_score: int | str | None = None
    buy_breakdown: list | None = None
    historical_data: dict | None = None
    algorithmic_insights: dict | None = None

@app.get("/api/search/{query}")
def search(query: str):
    q_key = query.lower().strip()
    if q_key in search_cache:
        return search_cache[q_key]
        
    result = search_companies(query)
    
    # Only cache if we got results, or if the query is very short (likely no results anyway)
    if result or len(q_key) <= 2:
        search_cache[q_key] = result
        
    return result

@app.get("/api/analyst/{ticker}")
def get_analyst(ticker: str):
    ticker_upper = ticker.upper()
    cache_key = f"analyst_{ticker_upper}_{CACHE_VERSION}"
    if cache_key in valuation_cache:
        return valuation_cache[cache_key]
    result = get_analyst_data(ticker_upper)
    valuation_cache[cache_key] = result
    return result

KV_REST_API_URL = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")

def kv_get(key: str):
    if not KV_REST_API_URL or not KV_REST_API_TOKEN:
        return None
    try:
        url = KV_REST_API_URL.rstrip('/')
        headers = {
            "Authorization": f"Bearer {KV_REST_API_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = ["GET", key]
        resp = requests.post(url, headers=headers, json=payload, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("result")
            if data:
                try:
                    return json.loads(data)
                except:
                    return data
    except Exception as e:
        print(f"KV GET Error: {e}")
    return None

def kv_set(key: str, value) -> bool:
    if not KV_REST_API_URL or not KV_REST_API_TOKEN:
        return False
    try:
        url = KV_REST_API_URL.rstrip('/')
        headers = {
            "Authorization": f"Bearer {KV_REST_API_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = ["SET", key, json.dumps(value)]
        resp = requests.post(url, headers=headers, json=payload, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"KV SET Error: {e}")
    return False

@app.get("/api/watchlist")
def get_watchlist():
    data = kv_get("watchlist")
    if data is not None:
        return data

    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

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
            "computed": req.computed
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


@app.get("/api/valuation/{ticker}", response_model=ValuationResponse)
def get_valuation(ticker: str, wacc: float = None):
    try:
        ticker_upper = ticker.upper()
        cache_key = f"val_{ticker_upper}_{wacc}_{CACHE_VERSION}"
        if cache_key in valuation_cache:
            return valuation_cache[cache_key]

        # 1. Scrape Yahoo Data
        data = get_company_data(ticker)
        if not data or not data.get("current_price"):
            raise HTTPException(status_code=404, detail=f"Data not found for {ticker}")
            
        current_price = data["current_price"]
    
        # 2. Get Competitors for Relative Valuation
        sector = data.get("sector")
        industry = data.get("industry")
        target_market_cap = data.get("market_cap") or 0.0
        peers_data = get_competitors_data(ticker, sector, industry, float(target_market_cap))
        market_data = get_market_averages()
        
        # 3. Compute Valuations
        # Peter Lynch (Refined with 3Y Projection - Nasdaq Default)
        # Use Nasdaq 3Y CAGR as primary source for Multiple
        eps_growth_estimated = data.get("eps_growth_nasdaq_3y")
        if eps_growth_estimated is None:
            eps_growth_estimated = data.get("eps_growth_3y") or data.get("eps_growth") or 0.05
        
        lynch_period_label = "Nasdaq 3Y Forecast" if data.get("eps_growth_nasdaq_3y") else ("3-Year Hist. Avg" if data.get("eps_growth_3y") else "Analyst Est.")
        
        
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

        pe_historic = data.get("pe_historic") or data.get("pe_ratio")
        lynch_result = calculate_peter_lynch(current_price, data.get("trailing_eps"), eps_growth_estimated, pe_historic, sector_median_pe)
        lynch_fwd_pe = lynch_result.get("fwd_pe")
        lynch_fair_value = lynch_result.get("fair_value")
        lynch_status = lynch_result.get("status")
        
        # PEG Valuation (Sector-based)
        eps_base = data.get("trailing_eps") or data.get("forward_eps") or 0
        current_pe = current_price / eps_base if eps_base > 0 else 0
        # Use Yahoo 5Y Consensus as primary source for PEG
        eps_growth_rate_peg = data.get("eps_growth_5y_consensus")
        
        # Fallback to Nasdaq 3Y if 5Y is missing (User requested)
        if eps_growth_rate_peg is None:
            eps_growth_rate_peg = data.get("eps_growth_nasdaq_3y")
            
        if eps_growth_rate_peg is None:
            eps_growth_rate_peg = data.get("eps_growth_5y") or data.get("eps_growth") or 0.05
            
        peg_period_label = "Yahoo 5Y Cons." if data.get("eps_growth_5y_consensus") else ("Nasdaq 3Y Forecast" if data.get("eps_growth_nasdaq_3y") else ("5-Year Hist. Avg" if data.get("eps_growth_5y") else "Analyst Est."))
        company_peg = current_pe / (eps_growth_rate_peg * 100) if eps_growth_rate_peg > 0 else 0
        
        # Calculate Industry PEG from peers + Target Company
        valid_pegs = []
        if company_peg > 0:
            valid_pegs.append(float(company_peg))
        
        if peers_data:
            for p in peers_data:
                v = p.get('peg_ratio')
                if v is not None and isinstance(v, (int, float)) and math.isfinite(v) and v > 0:
                    valid_pegs.append(float(v))
        
        industry_peg = statistics.median(valid_pegs) if valid_pegs else None
        peg_value = calculate_peg_fair_value(current_price, company_peg, industry_peg)
        
        # Relative Valuation (P/E Based currently)
        relative_value = calculate_relative_valuation(ticker, data, peers_data)
        
        # DCF
        # For DCF, we need FCF, Growth, WACC (discount_rate), terminal growth
        # We will use simple defaults if missing
        fcf = data.get("fcf")
        shares = data.get("shares_outstanding")
        eps_growth = data.get("eps_growth", 0.05) if data.get("eps_growth") is not None else 0.05
        
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
        
        if fcf and shares and fcf > 0:
            # 5 Year Calculation (Default for Dashboard)
            res_5 = calculate_dcf(fcf, eps_growth, discount_rate, perpetual_growth, shares, data.get("total_cash"), data.get("total_debt"), years=5)
            sens_5 = calculate_dcf_sensitivity(fcf, eps_growth, shares, data.get("total_cash"), data.get("total_debt"), 5, discount_rate, perpetual_growth)
            rev_5 = calculate_reverse_dcf(current_price, fcf, discount_rate, perpetual_growth, shares, data.get("total_cash"), data.get("total_debt"), 5)
            
            if res_5:
                dcf_value = res_5.get("fair_value")
                dcf_5yr = {
                    "result": res_5,
                    "sensitivity": sens_5,
                    "reverse_dcf": rev_5
                }
                
            # 10 Year Calculation 
            res_10 = calculate_dcf(fcf, eps_growth, discount_rate, perpetual_growth, shares, data.get("total_cash"), data.get("total_debt"), years=10)
            sens_10 = calculate_dcf_sensitivity(fcf, eps_growth, shares, data.get("total_cash"), data.get("total_debt"), 10, discount_rate, perpetual_growth)
            rev_10 = calculate_reverse_dcf(current_price, fcf, discount_rate, perpetual_growth, shares, data.get("total_cash"), data.get("total_debt"), 10)
            
            if res_10:
                dcf_10yr = {
                    "result": res_10,
                    "sensitivity": sens_10,
                    "reverse_dcf": rev_10
                }
        # historical trends
        historical_trends = data.get("historical_trends", [])
            
        # Stabilize Fair Value with Sector-Aware Weighting
        sector = data.get("company_profile", {}).get("sector", "")
        
        # Define base sector weights
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
            margin_of_safety = ((fair_value - current_price) / fair_value) * 100
        else:
            fair_value = None
            margin_of_safety = None
            
        # Add bounds handling to avoid infinite or NaN
        def sanitize(val):
            if val is None or math.isnan(val) or math.isinf(val):
                return None
            return round(val, 2)
            
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
                val = p.get('peg_ratio')
                if val is not None and isinstance(val, (int, float)) and math.isfinite(val):
                    valid_pegs.append(float(val))
            
            if valid_pegs:
                median_peer_peg = statistics.median(valid_pegs)

        # Calculate Current PE for PEG transparency
        current_pe = current_price / data.get("trailing_eps") if data.get("trailing_eps") and data.get("trailing_eps") > 0 else None

        # 5. Build Formula Data for Transparency
        fair_value_sector_pe = None
        if lynch_result.get("fwd_eps") and median_peer_pe:
            fair_value_sector_pe = lynch_result.get("fwd_eps") * median_peer_pe

        def _format_dcf_payload(dcf_dict):
            if not dcf_dict or not dcf_dict.get("result"):
                return None
            res = dcf_dict["result"]
            sens = dcf_dict["sensitivity"]
            rev = dcf_dict["reverse_dcf"]
            return {
                "fcf_years": [sanitize(x) for x in res.get("fcf_years", [])],
                "pv_fcf_years": [sanitize(x) for x in res.get("pv_fcf_years", [])],
                "terminal_value": sanitize(res.get("terminal_value")),
                "pv_terminal_value": sanitize(res.get("pv_terminal_value")),
                "sum_pv_cf": sanitize(res.get("sum_pv_cf")),
                "enterprise_value": sanitize(res.get("enterprise_value")),
                "total_cash": sanitize(res.get("total_cash")),
                "total_debt": sanitize(res.get("total_debt")),
                "equity_value": sanitize(res.get("equity_value")),
                "intrinsic_value": sanitize(res.get("fair_value")),
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
                "status": lynch_status
            },
            "peg": {
                "current_pe": sanitize(current_pe),
                "eps_growth_estimated": sanitize(eps_growth_rate_peg),
                "eps_growth_period": peg_period_label,
                "current_peg": sanitize(company_peg) if company_peg > 0 else None,
                "industry_peg": sanitize(industry_peg),
                "fair_value": sanitize(peg_value),
                "margin_of_safety": sanitize(((peg_value - current_price) / peg_value * 100)) if peg_value and peg_value > 0 else None
            },
            "dcf": {
                "fcf": sanitize(fcf),
                "eps_growth_estimated": sanitize(eps_growth),
                "eps_growth_period": data.get("eps_growth_period", "Next Year"),
                "discount_rate": discount_rate,
                "perpetual_growth": perpetual_growth,
                "shares_outstanding": shares,
                "historic_buyback_rate": sanitize(data.get("historic_buyback_rate")),
                "5yr": _format_dcf_payload(dcf_5yr) if dcf_5yr else None,
                "10yr": _format_dcf_payload(dcf_10yr) if dcf_10yr else None,
                "intrinsic_value": sanitize(dcf_value),
                "margin_of_safety": sanitize(((dcf_value - current_price) / dcf_value * 100)) if dcf_value and dcf_value > 0 else None,
                "current_price": sanitize(current_price)
            }
        ,
        "relative": {
            "company_eps": sanitize(data.get("trailing_eps")),
            "company_trailing_pe": sanitize(pe_historic),
            "peers": [p.get("ticker", p) if isinstance(p, dict) else p for p in peers_data] if peers_data else [],
            "median_peer_pe": sanitize(median_peer_pe),
            "median_peer_peg": sanitize(median_peer_peg),
            "mean_peer_pe": sanitize(mean_peer_pe),
            "market_pe_trailing": sanitize(market_data.get("trailing_pe")),
            "market_pe_forward": sanitize(market_data.get("forward_pe"))
        }
    }

    # 6. Compute Comprehensive Scoring
        h_result = calculate_health_score(data)
        b_result = calculate_buy_score({"margin_of_safety": margin_of_safety}, data)
        
        health_score = h_result.get("total") if isinstance(h_result, dict) else h_result
        health_breakdown = h_result.get("breakdown") if isinstance(h_result, dict) else []
        
        buy_score = b_result.get("total") if isinstance(b_result, dict) else b_result
        buy_breakdown = b_result.get("breakdown") if isinstance(b_result, dict) else []

        # 7. Algorithmic Insights Generation
        all_breakdowns = health_breakdown + buy_breakdown
        top_strengths = []
        risk_factors = []
        
        if all_breakdowns:
            # Strengths: items with max points
            max_point_items = [b for b in all_breakdowns if b.get("points") == b.get("max_points") and b.get("max_points", 0) > 0]
            # Sort by highest max_points just to show the most impactful ones first
            max_point_items.sort(key=lambda x: x.get("max_points", 0), reverse=True)
            top_strengths = max_point_items[:3]
            
            # Risks: items with 0 points
            zero_point_items = [b for b in all_breakdowns if b.get("points") == 0]
            if zero_point_items:
                risk_factors = zero_point_items[:3]
            else:
                # Fallback: lowest partial points if no 0s
                all_sorted = sorted(all_breakdowns, key=lambda x: x.get("points", 100))
                risk_factors = all_sorted[:2]

        response_data = {
            "ticker": data["ticker"],
            "name": data["name"],
            "current_price": sanitize(current_price),
            "fair_value": sanitize(fair_value),
            "margin_of_safety": sanitize(margin_of_safety),
            "baseline_weights": base_weights,
            "dcf_value": sanitize(dcf_value),
            "relative_value": sanitize(relative_value),
            "lynch_fwd_pe": sanitize(lynch_fwd_pe),
            "lynch_fair_value": sanitize(lynch_pe20_val),
            "lynch_status": lynch_status,
            "peter_lynch": formula_data["peter_lynch"],
            "peg_value": sanitize(peg_value),
            "company_profile": {
                "industry": data.get("industry") or "N/A",
                "sector": data.get("sector") or "N/A",
                "market_cap": data.get("shares_outstanding", 0) * current_price if data.get("shares_outstanding") else None,
                "current_pe": sanitize(data.get("forward_pe")),
                "trailing_pe": sanitize(pe_historic),
                "current_eps": sanitize(data.get("forward_eps")),
                "trailing_eps": sanitize(data.get("trailing_eps")),
                "historic_eps_growth": sanitize(data.get("historic_eps_growth")),
                "historic_fcf_growth": sanitize(data.get("historic_fcf_growth")),
                "debt_to_equity": sanitize(data.get("debt_to_equity")),
                "shares_outstanding": sanitize(data.get("shares_outstanding")),
                "buyback_rate": sanitize(data.get("historic_buyback_rate") * 100 if data.get("historic_buyback_rate") else None),
                "dividend_yield": sanitize(data.get("dividend_yield") * 100 if data.get("dividend_yield") and data.get("dividend_yield") < 0.30 else data.get("dividend_yield")),
                "operating_margin": sanitize(data.get("operating_margin")),
                "net_margin": sanitize(data.get("net_margin")),
                "payout_ratio": sanitize(data.get("payout_ratio")),
                "insider_ownership": sanitize(data.get("insider_ownership")),
                "next_earnings_date": data.get("next_earnings_date"),
                "business_summary": data.get("business_summary"),
                "dividend_streak": data.get("dividend_streak"),
                "dividend_cagr_5y": data.get("dividend_cagr_5y"),
                "red_flags": data.get("red_flags"),
                "competitors": [p.get("ticker", p) if isinstance(p, dict) else p for p in peers_data] if peers_data else [],
                "competitor_metrics": peers_data if peers_data else []
            },
            "historical_trends": historical_trends,
            "historical_data": data.get("historical_data"),
            "formula_data": formula_data,
            "health_score": health_score,
            "health_breakdown": health_breakdown,
            "buy_score": buy_score,
            "buy_breakdown": buy_breakdown,
            "algorithmic_insights": {
                "top_strengths": top_strengths,
                "risk_factors": risk_factors
            }
        }
    except Exception as e:
        import traceback
        print(f"VALUATION CRASH for {ticker}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Backend Error for {ticker}: {str(e)}")

    valuation_cache[cache_key] = response_data
    return response_data

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
