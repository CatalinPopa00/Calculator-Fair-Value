
import sys
import os
import json

# Add api directory to path
sys.path.append(os.path.abspath('api'))

from scraper.yahoo import get_company_data

def test_ko():
    print("Testing KO data extraction (STABLE COMPANY)...")
    data = get_company_data("KO", fast_mode=False)
    
    print(f"\nTicker: {data.get('ticker')}")
    print(f"GAAP EPS (TTM): {data.get('trailing_eps')}")
    print(f"Adjusted EPS (TTM): {data.get('adjusted_eps')}")
    
    hd = data.get('historical_data', {})
    print("\nHistorical Data (Charts):")
    for i in range(len(hd.get('years', []))):
        print(f"  {hd['years'][i]}: EPS={hd['eps'][i]}")

if __name__ == "__main__":
    test_ko()
