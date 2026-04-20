
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api')))

from scraper.yahoo import get_company_data

def check_estimations():
    ticker = "HIMS"
    data = get_company_data(ticker, fast_mode=False)
    
    print(f"Ticker: {ticker}")
    print(f"Current Adjusted Anchor (2025): {data.get('adjusted_eps')}")
    print(f"Projected Growth (Engine): {data.get('growth_eps') * 100:.2f}%")
    
    print("\nAnalyst Estimations Table (Backend Data):")
    # In our project, analyst data is usually in 'historical_anchors' (for historical) 
    # and we should check how 'forward_eps' or similar is returned.
    
    # Let's look at the historical_anchors to see the progression
    for anchor in data.get('historical_anchors', []):
        y = anchor.get('year')
        eps = anchor.get('eps')
        print(f"Year {y}: EPS={eps}")

if __name__ == "__main__":
    check_estimations()
