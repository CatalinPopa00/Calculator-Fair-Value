
import sys
import os
import json
import datetime

# Add api directory to path
sys.path.append(os.path.abspath('api'))

from scraper.yahoo import get_nasdaq_earnings_surprise

def debug_hims_quarters():
    ticker = "HIMS"
    print(f"Fetching Nasdaq surprises for {ticker}...")
    rows = get_nasdaq_earnings_surprise(ticker)
    
    print("\nNasdaq Reported Quarters:")
    for row in rows:
        print(f"  Date: {row.get('dateReported')}, EPS: {row.get('eps')}")
        
if __name__ == "__main__":
    debug_hims_quarters()
