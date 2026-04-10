
import sys
import os
import json

# Add the directory to sys.path
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d')

from api.scraper.yahoo import get_company_data

if __name__ == "__main__":
    ticker = "ADBE"
    try:
        data = get_company_data(ticker)
        print(f"Ticker: {ticker}")
        print(f"Price: {data.get('current_price')}")
        print(f"Adjusted EPS (2025): {data.get('adjusted_eps')}")
        
        hist = data.get('historical_data', {})
        years = hist.get('years', [])
        eps = hist.get('eps', [])
        
        print("\nHistorical Table Data:")
        for y, e in zip(years, eps):
            print(f"Year {y}: EPS {e}")
            
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()
