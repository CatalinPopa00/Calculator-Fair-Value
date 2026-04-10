
import sys
import os
import datetime
import pandas as pd

# Add the directory to sys.path
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d')

import yfinance as yf
from scraper.yahoo import get_analyst_data, get_nasdaq_historical_eps

def diagnose_adbe():
    ticker = "ADBE"
    print(f"--- DIAGNOSING {ticker} ---")
    
    # 1. Fetch yfinance financials (GAAP)
    stock = yf.Ticker(ticker)
    financials = stock.financials
    print("\n[Source 1] GAAP EPS (yfinance financials):")
    if financials is not None and not financials.empty:
        # Search for 'Diluted EPS' or 'Basic EPS'
        eps_row = None
        for row in financials.index:
            if 'EPS' in str(row).upper():
                eps_row = financials.loc[row]
                print(f"Row: {row}")
                for col, val in eps_row.items():
                    print(f"  {col.year}: {val}")
                break
    else:
        print("No financials found.")

    # 2. Fetch Nasdaq Surprise (Non-GAAP)
    print("\n[Source 2] Non-GAAP EPS (Nasdaq Surprise API):")
    nq_hist = get_nasdaq_historical_eps(ticker)
    if nq_hist:
        # Group by year
        # ADBE Fiscal Year ends in November. 
        # Dec, Jan, Feb -> Q1?
        # Let's see raw dates
        for item in nq_hist:
            print(f"  Date: {item['date'].strftime('%Y-%m-%d')}, EPS: {item['eps']}")
    else:
        print("No Nasdaq data found.")

    # 3. Run full platform logic
    print("\n[Result] Platform 'Historical Anchors' (Consolidated):")
    result = get_analyst_data(ticker)
    anchors = result.get('historical_anchors', [])
    for a in anchors:
        print(f"  Year: {a['year']}, Revenue(B): {a['revenue_b']}, EPS*: {a['eps']}, Margin: {a['net_margin_pct']}")

if __name__ == "__main__":
    diagnose_adbe()
