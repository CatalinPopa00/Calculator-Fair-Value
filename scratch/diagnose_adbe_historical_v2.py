
import sys
import os
import datetime
import pandas as pd
import json

# Add the directory to sys.path
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d')

import yfinance as yf
from scraper.yahoo import get_analyst_data, get_nasdaq_historical_eps

def diagnose_adbe():
    ticker = "ADBE"
    print(f"--- DIAGNOSING {ticker} ---")
    
    # Check Nasdaq Surprise raw data structure
    import requests
    url = f"https://api.nasdaq.com/api/company/{ticker}/earnings-surprise"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    }
    resp = requests.get(url, headers=headers, timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        # The 'chart' usually contains surprise % or surprise index
        # The 'rows' usually contains the actual values
        rows = data.get('data', {}).get('earningsSurpriseTable', {}).get('rows', [])
        print("\n[Raw] Nasdaq Earnings Surprise Table Rows:")
        for r in rows[:5]:
            print(f"  {r}")
    
    # Platform Result
    result = get_analyst_data(ticker)
    if "error" in result:
        print(f"ERROR in get_analyst_data: {result['error']}")
        return

    anchors = result.get('historical_anchors', [])
    print(f"\n[Result] Found {len(anchors)} Historical Anchors:")
    for a in anchors:
        print(f"  Year: {a['year']}, Rev(B): {a.get('revenue_b')}, EPS*: {a.get('eps')}, Margin: {a.get('net_margin_pct')}")

    # Aggregated Non-GAAP history
    # The get_analyst_data prints its own DEBUG normally, but let's see why it's empty
    print("\n[Internal] Adjusted History Map:")
    # We can't easily see internal variables, so I'll trust the summary for now.

if __name__ == "__main__":
    diagnose_adbe()
