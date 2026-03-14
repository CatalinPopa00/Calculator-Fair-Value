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
# Valuation cache (24 hours TTL)
valuation_cache = TTLCache(maxsize=1000, ttl=24 * 60 * 60)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WATCHLIST_FILE = "watchlist.json"

class WatchlistRequest(BaseModel):
    tickers: list[str]

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
    if query in search_cache:
        return search_cache[query]
    result = search_companies(query)
    search_cache[query] = result
    return result

@app.get("/api/analyst/{ticker}")
def get_analyst(ticker: str):
    ticker_upper = ticker.upper()
    cache_key = f"analyst_{ticker_upper}"
    if cache_key in valuation_cache:
        return valuation_cache[cache_key]
    result = get_analyst_data(ticker_upper)
    valuation_cache[cache_key] = result
    return result

@app.get("/api/watchlist")
def get_watchlist():
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
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(req.tickers, f)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/valuation/{ticker}", response_model=ValuationResponse)
def get_valuation(ticker: str, wacc: float = None):
    ticker_upper = ticker.upper()
    if ticker_upper in valuation_cache:
        return valuation_cache[ticker_upper]

    # 1. Scrape Yahoo Data
    data = get_company_data(ticker)
    if not data or not data.get("current_price"):
        raise HTTPException(status_code=404, detail="Company or price data not found")
        
    current_price = data["current_price"]
    
    # 2. Get Competitors for Relative Valuation
    sector = data.get("sector")
    industry = data.get("industry")
    target_market_cap = data.get("market_cap") or 0.0
    peers_data = get_competitors_data(ticker, sector, industry, float(target_market_cap))
    market_data = get_market_averages()
    
    # 3. Compute Valuations
    # Peter Lynch
    pe_historic = data.get("pe_ratio") # Usually trailingPE is a good proxy for historic if true 5-yr avg is missing
    lynch_result = calculate_peter_lynch(current_price, data.get("trailing_eps"), data.get("eps_growth"), pe_historic)
    lynch_fwd_pe = lynch_result.get("fwd_pe")
    lynch_fair_value = lynch_result.get("fair_value")
    lynch_status = lynch_result.get("status")
    
    # PEG Rule of Three
    peg_value = calculate_peg_fair_value(data.get("trailing_eps"), data.get("eps_growth"))
    
    # Relative Valuation (P/E Based currently)
    relative_value = calculate_relative_valuation(ticker, data, peers_data)
    
    # DCF
    # For DCF, we need FCF, Growth, WACC (discount_rate), terminal growth
    # We will use simple defaults if missing
    fcf = data.get("fcf")
    shares = data.get("shares_outstanding")
    eps_growth = data.get("eps_growth", 0.05) if data.get("eps_growth") is not None else 0.05
    
    dcf_sensitivity = []
    reverse_dcf_growth = None
    dcf_value = None
    dcf_result = None
    
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
        dcf_result = calculate_dcf(fcf, eps_growth, discount_rate, perpetual_growth, shares, data.get("total_cash"), data.get("total_debt"))
        if dcf_result:
            dcf_value = dcf_result.get("fair_value")
            
        dcf_sensitivity = calculate_dcf_sensitivity(fcf, eps_growth, shares, data.get("total_cash"), data.get("total_debt"), 5, discount_rate, perpetual_growth)
        reverse_dcf_growth = calculate_reverse_dcf(current_price, fcf, discount_rate, perpetual_growth, shares, data.get("total_cash"), data.get("total_debt"), 5)
        

        
    # historical trends
    historical_trends = data.get("historical_trends", [])
        
    # Average the valid valuation methods using Peter Lynch PE=20 per user request
    lynch_pe20_val = lynch_result.get("fair_value_pe_20")
    valid_methods = [v for v in (lynch_pe20_val, peg_value, relative_value, dcf_value) if v is not None and v > 0]
    
    if valid_methods:
        fair_value = sum(valid_methods) / len(valid_methods)
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
        valid_pes = [p.get('pe_ratio') for p in peers_data if p.get('pe_ratio')]
        if valid_pes:
            median_peer_pe = statistics.median(valid_pes)
            mean_peer_pe = sum(valid_pes) / len(valid_pes)
            
        valid_pegs = [p.get('peg_ratio') for p in peers_data if p.get('peg_ratio') is not None]
        print(f"Debug: peers_data={[(p.get('ticker'), p.get('peg_ratio')) for p in peers_data]}")
        print(f"Debug: valid_pegs={valid_pegs}")
        if valid_pegs:
            median_peer_peg = statistics.median(valid_pegs)

    # Calculate Current PE for PEG transparency
    current_pe = current_price / data.get("trailing_eps") if data.get("trailing_eps") and data.get("trailing_eps") > 0 else None

    # 5. Build Formula Data for Transparency
    fair_value_sector_pe = None
    if lynch_result.get("fwd_eps") and median_peer_pe:
        fair_value_sector_pe = lynch_result.get("fwd_eps") * median_peer_pe

    formula_data = {
        "peter_lynch": {
            "current_price": sanitize(current_price),
            "trailing_eps": sanitize(data.get("trailing_eps")),
            "fwd_eps": sanitize(lynch_result.get("fwd_eps")),
            "eps_growth_estimated": sanitize(data.get("eps_growth")),
            "eps_growth_period": data.get("eps_growth_period", "Next Year"),
            "historic_pe": sanitize(pe_historic),
            "fwd_pe": sanitize(lynch_fwd_pe),
            "fair_value": sanitize(lynch_fair_value),
            "fair_value_pe_20": sanitize(lynch_pe20_val),
            "fair_value_sector_pe": sanitize(fair_value_sector_pe),
            "sector_pe": sanitize(median_peer_pe),
            "status": lynch_status
        },
        "peg": {
            "company_eps": sanitize(data.get("trailing_eps")),
            "current_pe": sanitize(current_pe),
            "eps_growth_estimated": sanitize(data.get("eps_growth")),
            "eps_growth_period": data.get("eps_growth_period", "Next Year"),
            "current_peg": sanitize(current_pe / (data.get("eps_growth") * 100)) if current_pe and data.get("eps_growth") and data.get("eps_growth") > 0 else None,
            "fair_value": sanitize(peg_value)
        },
        "dcf": {
            "fcf": sanitize(fcf),
            "eps_growth_estimated": sanitize(eps_growth),
            "eps_growth_period": data.get("eps_growth_period", "Next Year"),
            "discount_rate": discount_rate,
            "perpetual_growth": perpetual_growth,
            "shares_outstanding": shares,
            "historic_buyback_rate": sanitize(data.get("historic_buyback_rate")),
            "fcf_years": [sanitize(x) for x in dcf_result.get("fcf_years", [])] if dcf_result else [],
            "pv_fcf_years": [sanitize(x) for x in dcf_result.get("pv_fcf_years", [])] if dcf_result else [],
            "terminal_value": sanitize(dcf_result.get("terminal_value")) if dcf_result else None,
            "pv_terminal_value": sanitize(dcf_result.get("pv_terminal_value")) if dcf_result else None,
            "sum_pv_cf": sanitize(dcf_result.get("sum_pv_cf")) if dcf_result else None,
            "enterprise_value": sanitize(dcf_result.get("enterprise_value")) if dcf_result else None,
            "total_cash": sanitize(dcf_result.get("total_cash")) if dcf_result else None,
            "total_debt": sanitize(dcf_result.get("total_debt")) if dcf_result else None,
            "equity_value": sanitize(dcf_result.get("equity_value")) if dcf_result else None,
            "intrinsic_value": sanitize(dcf_value),
            "current_price": sanitize(current_price),
            "margin_of_safety": sanitize(((dcf_value - current_price) / dcf_value * 100)) if dcf_value and dcf_value > 0 else None,
            "sensitivity_matrix": [
                {
                    "discount_rate": sanitize(row["discount_rate"]),
                    "values": [{"perpetual_growth": sanitize(v["perpetual_growth"]), "fair_value": sanitize(v["fair_value"])} for v in row["values"]]
                } for row in dcf_sensitivity
            ] if dcf_sensitivity else [],
            "reverse_dcf_growth": sanitize(reverse_dcf_growth) if reverse_dcf_growth is not None else None
        },
        "relative": {
            "company_eps": sanitize(data.get("trailing_eps")),
            "company_trailing_pe": sanitize(pe_historic),
            "peers_used": [p.get("ticker", p) if isinstance(p, dict) else p for p in peers_data] if peers_data else [],
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
        "dcf_value": sanitize(dcf_value),
        "relative_value": sanitize(relative_value),
        "lynch_fwd_pe": sanitize(lynch_fwd_pe),
        "lynch_fair_value": sanitize(lynch_pe20_val),
        "lynch_status": lynch_status,
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
            "dividend_yield": sanitize(data.get("dividend_yield") * 100 if data.get("dividend_yield") and data.get("dividend_yield") < 0.20 else data.get("dividend_yield")),
            "competitors": [p.get("ticker", p) if isinstance(p, dict) else p for p in peers_data] if peers_data else []
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
    
    valuation_cache[ticker_upper] = response_data
    return response_data

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
