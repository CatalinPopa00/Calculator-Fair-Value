
import sys
import os
import json

# Add the directory to sys.path
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d')

from api.scraper.yahoo import get_company_data, get_analyst_data

if __name__ == "__main__":
    ticker = "ADBE"
    c_data = get_company_data(ticker)
    base_eps = c_data.get('adjusted_eps')
    q_map = c_data.get('raw_quarterly_history')
    
    print(f"Base EPS (FY 2025): {base_eps}")
    
    analyst_result = get_analyst_data(ticker, base_eps=base_eps, q_history=q_map)
    eps_proj = analyst_result.get('eps_estimates', [])
    
    print("\nEPS Projections (Sync Check):")
    for p in eps_proj:
        growth = f"{p['growth']*100:.1f}%" if p['growth'] is not None else "N/A"
        print(f"Period: {p['period']}, Avg: {p['avg']}, Growth: {growth}")
