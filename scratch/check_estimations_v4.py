
import os
import sys
import json

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api')))

from scraper.yahoo import get_company_data

def check_estimations():
    ticker = "HIMS"
    data = get_company_data(ticker, fast_mode=False)
    
    print(f"Ticker: {ticker}")
    print(f"Adjusted EPS (TTM): {data.get('adjusted_eps')}")
    print(f"EPS Growth (Main): {data.get('eps_growth')}")
    
    # Check for analyst_data
    # In index.py, get_company_data result is returned.
    # Let's see if there is an 'eps_estimates' table in the top level (merged from analyst_data)
    if 'eps_estimates' in data:
        print("\nEPS Estimates Table:")
        for est in data['eps_estimates']:
            print(f"  Period: {est.get('period')}, Avg: {est.get('avg')}, Growth: {est.get('growth')}")

if __name__ == "__main__":
    check_estimations()
