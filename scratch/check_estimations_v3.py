
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api')))

from scraper.yahoo import get_company_data

def check_estimations():
    ticker = "HIMS"
    data = get_company_data(ticker, fast_mode=False)
    
    print(f"Ticker: {ticker}")
    print(f"Adjusted EPS (TTM): {data.get('adjusted_eps')}")
    print(f"Growth EPS (Engine): {data.get('growth_eps')}")
    
    print("\nHistorical Anchors (Chart Baseline):")
    for a in data.get('historical_anchors', []):
        print(f"  {a.get('year')}: {a.get('eps')}")
        
    print(f"\nForward EPS (FY1): {data.get('forward_eps')}")
    print(f"Forward Growth: {data.get('forward_growth')}")
    
    # Check if we have Analyst Estimates in the response
    # Often it is in 'analyst_estimates' or similar
    if 'analyst_data' in data:
        print("\nAnalyst Data EPS Estimates:")
        for est in data['analyst_data'].get('eps_estimates', []):
            print(f"  {est.get('period')}: {est.get('avg')} (Growth: {est.get('growth')})")

if __name__ == "__main__":
    check_estimations()
