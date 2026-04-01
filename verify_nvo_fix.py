import sys
import os
import pandas as pd

# Add the project root to sys.path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from api.scraper.yahoo import get_company_data

def verify_ticker(ticker):
    print(f"\n--- Verifying {ticker} ---")
    data = get_company_data(ticker)
    
    print(f"Name: {data.get('name')}")
    print(f"Price: {data.get('current_price')}")
    print(f"Trailing EPS: {data.get('trailing_eps')}")
    print(f"Adjusted EPS: {data.get('adjusted_eps')}")
    print(f"Forward EPS: {data.get('forward_eps')}")
    print(f"Growth Rate: {data.get('eps_growth') * 100:.2f}%")
    print(f"Growth Period: {data.get('eps_growth_period')}")
    
    # Specific assertions for NVO
    if ticker == 'NVO':
        # 3.54 should be the base, and growth should NOT be 80%
        if data.get('eps_growth') > 0.5:
            print("FAILED: Growth rate still looks too high!")
        else:
            print("SUCCESS: Growth rate looks sane.")

if __name__ == "__main__":
    verify_ticker('NVO')
    verify_ticker('AAPL')
