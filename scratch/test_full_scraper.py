
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
        # Print keys to see if we got data
        print(f"Data keys: {list(data.keys())}")
        print(f"Name: {data.get('name')}")
        print(f"Price: {data.get('current_price')}")
        print(f"EPS Growth: {data.get('eps_growth')}")
        print(f"Growth Period: {data.get('eps_growth_period')}")
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()
