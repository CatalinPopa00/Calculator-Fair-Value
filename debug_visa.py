import asyncio
import os
import sys
import json

# Add parent dir to sys.path to import api modules
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_company_data, get_competitors_data, get_market_averages
from api.models.valuation import calculate_peter_lynch, calculate_peg_fair_value, calculate_relative_valuation, calculate_dcf
import math
import statistics

async def debug_visa():
    ticker = "V"
    data = get_company_data(ticker)
    
    current_price = data["current_price"]
    sector = data.get("sector")
    industry = data.get("industry")
    market_cap = data.get("market_cap") or 0.0
    
    print(f"Price: {current_price}, Sector: {sector}, Industry: {industry}")
    
    peers_data = get_competitors_data(ticker, sector, industry, float(market_cap), include_growth=True)
    print(f"Peers found: {len(peers_data) if peers_data else 0}")
    
    # Check Lynch
    eps_growth_estimated = data.get("eps_growth_nasdaq_3y") or data.get("eps_growth_3y") or data.get("eps_growth") or 0.05
    valid_pes = []
    if peers_data:
        for p in peers_data:
            v = p.get('pe_ratio')
            if v and v > 0: valid_pes.append(v)
    if data.get("pe_ratio") and data.get("pe_ratio") > 0:
        valid_pes.append(data.get("pe_ratio"))
    sector_median_pe = statistics.median(valid_pes) if valid_pes else 20.0
    
    pe_historic = data.get("pe_historic") or data.get("pe_ratio")
    eps_for_valuation = data.get("adjusted_eps") or data.get("trailing_eps")
    lynch_result = calculate_peter_lynch(current_price, eps_for_valuation, eps_growth_estimated, pe_historic, sector_median_pe)
    print(f"Lynch Val: {lynch_result.get('fair_value')}")
    
    # Check PEG
    eps_growth_rate_peg = data.get("eps_growth_5y_consensus") or data.get("eps_growth_nasdaq_3y") or 0.05
    current_pe = current_price / eps_for_valuation if eps_for_valuation > 0 else 0
    company_peg = current_pe / (eps_growth_rate_peg * 100) if eps_growth_rate_peg > 0 else 0
    valid_pegs = [company_peg] if company_peg > 0 else []
    if peers_data:
        for p in peers_data:
            v = p.get('peg_ratio')
            if v and v > 0: valid_pegs.append(v)
    industry_peg = statistics.median(valid_pegs) if valid_pegs else None
    peg_value = calculate_peg_fair_value(current_price, company_peg, industry_peg)
    print(f"PEG Val: {peg_value}")
    
    # Relative
    relative_value = calculate_relative_valuation(ticker, data, peers_data)
    print(f"Relative Val: {relative_value}")
    
    # Weights
    if sector == "Financial Services":
        base_weights = {"lynch": 0.45, "relative": 0.45, "peg": 0.10, "dcf": 0.0}
    else:
        base_weights = {"lynch": 0.25, "relative": 0.25, "peg": 0.25, "dcf": 0.25}
        
    method_map = {
        "lynch": lynch_result.get("fair_value_pe_20"),
        "peg": peg_value,
        "relative": relative_value,
        "dcf": None # Assuming DCF 0 for Financials
    }
    
    total_weight = 0
    weighted_sum = 0
    for key, val in method_map.items():
        print(f"Method {key}: val={val}, weight={base_weights.get(key)}")
        if val is not None and val > 0:
            w = base_weights.get(key, 0)
            weighted_sum += val * w
            total_weight += w
            
    print(f"Weighted Sum: {weighted_sum}, Total Weight: {total_weight}")

if __name__ == "__main__":
    asyncio.run(debug_visa())
