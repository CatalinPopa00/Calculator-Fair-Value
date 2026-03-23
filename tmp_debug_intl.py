
import sys
import os
import json

sys.path.append(os.getcwd())
from api.scraper.yahoo import get_lightweight_company_data, get_company_data

def debug_international():
    tickers = ["MC.PA", "RMS.PA", "LVMUY"]
    for t in tickers:
        print(f"\n--- Debugging {t} ---")
        light = get_lightweight_company_data(t)
        print(f"Lightweight data: {json.dumps(light, indent=2)}")
        
        full = get_company_data(t)
        if full:
            print(f"Full data keys: {list(full.keys())}")
            print(f"Historical data check: {len(full.get('historical_data', {}).get('years', []))} years")
            print(f"Shares Outstanding: {full.get('shares_outstanding')}")
            
            # Check the last few years of chart data
            hist = full.get('historical_data', {})
            years = hist.get('years', [])
            shares = hist.get('shares', [])
            if years:
                print(f"Last years: {years[-3:]}")
                print(f"Last shares: {shares[-3:]}")

if __name__ == "__main__":
    debug_international()
