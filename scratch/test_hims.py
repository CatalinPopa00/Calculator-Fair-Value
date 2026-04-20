
import os
import sys
import datetime
import pandas as pd

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api')))

from scraper.yahoo import get_company_data

def test_company():
    ticker_symbol = sys.argv[1] if len(sys.argv) > 1 else "HIMS"
    print(f"Testing {ticker_symbol} data extraction...")
    data = get_company_data(ticker_symbol, fast_mode=False)
    
    print(f"\nTicker: {data.get('ticker')}")
    print(f"Name: {data.get('name')}")
    print(f"GAAP EPS (TTM): {data.get('trailing_eps')}")
    print(f"Adjusted EPS (TTM): {data.get('adjusted_eps')}")
    
    print("\nHistorical Data (Charts):")
    for yr, val in data.get("historical_data", {}).get("eps", {}).items():
        print(f"  {yr}: EPS={val}")
        
    print(f"\nHistorical Anchors Count: {len(data.get('historical_anchors', []))}")
    for anchor in data.get('historical_anchors', []):
        print(f"  Year: {anchor.get('year')}")
        print(f"    Rev: {anchor.get('revenue')}B, EPS: {anchor.get('eps')}, FCF: {anchor.get('fcf')}B")
        print(f"    Margin: {anchor.get('net_margin')}%, ROIC: {anchor.get('roic')}%")
        print(f"    Cash: {anchor.get('cash')}B, Debt: {anchor.get('debt')}B, Shares: {anchor.get('shares')}B")

if __name__ == "__main__":
    test_company()
