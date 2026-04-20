
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api')))

from scraper.yahoo import get_company_data, get_analyst_data, get_stock_info

def check_estimations():
    ticker = "HIMS"
    info = get_stock_info(ticker)
    # We need to simulate the arguments passed to get_analyst_data
    # In get_company_data: analyst_data = get_analyst_data(ticker_symbol, info, historical_data, fx_rate)
    
    # Let's just run get_company_data and inspect the internal analyst_data if we can, 
    # or just look at the return.
    data = get_company_data(ticker, fast_mode=False)
    
    print(f"Ticker: {ticker}")
    print(f"Adjusted EPS (TTM): {data.get('adjusted_eps')}")
    print(f"Growth EPS (Engine): {data.get('growth_eps')}")
    
    # The frontend uses 'historical_anchors' for the charts
    print("\nHistorical Anchors (Chart Baseline):")
    for a in data.get('historical_anchors', []):
        print(f"  {a.get('year')}: {a.get('eps')}")
        
    # The frontend uses a table for 'estimations' often derived from analyst_data
    # Let's check the analyst_data in the response if it's there
    # (Usually it's flattened into the main object)
    
    # Wait! I'll check my yahoo.py return for get_company_data
    print("\nEstimates Field in Result:")
    # The 'forward_eps' and 'forward_growth' are often used
    print(f"Forward EPS: {data.get('forward_eps')}")
    print(f"Forward Growth: {data.get('forward_growth')}")

if __name__ == "__main__":
    check_estimations()
