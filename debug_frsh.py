import sys
import os
import json
import pandas as pd

# Add the root directory to sys.path
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_nasdaq_comprehensive_estimates, get_analyst_data

def debug_frsh():
    ticker = "FRSH"
    print(f"--- Debugging {ticker} ---")
    
    # 1. Raw Nasdaq Data
    nq_data = get_nasdaq_comprehensive_estimates(ticker)
    print("\n[Nasdaq Yearly EPS Rows]")
    for row in nq_data.get("yearly_eps", []):
        print(row)
        
    # 2. Final Processed Analyst Data
    analyst_data = get_analyst_data(ticker)
    print("\n[Final Analyst EPS Estimates]")
    for est in analyst_data.get("eps_estimates", []):
        print(est)

if __name__ == "__main__":
    debug_frsh()
