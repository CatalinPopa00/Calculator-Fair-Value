
from scraper.yahoo import get_company_data
import json

def debug_meta():
    ticker = "META"
    print(f"Fetching {ticker} data...")
    data = get_company_data(ticker, fast_mode=False)
    
    print(f"Name: {data.get('name')}")
    print(f"Adjusted EPS (TTM): {data.get('adjusted_eps')}")
    print(f"Trailing EPS: {data.get('trailing_eps')}")
    
    print("\nHistorical Data:")
    hist = data.get('historical_data', {})
    years = hist.get('years', [])
    eps = hist.get('eps', [])
    for y, e in zip(years, eps):
        print(f"  {y}: {e}")

    print("\nProjections in historical_trends:")
    trends = data.get('historical_trends', [])
    for t in trends:
        if "Est" in str(t.get('year')):
            print(f"  {t.get('year')}: EPS={t.get('eps')}, Growth={t.get('eps_growth')}")

if __name__ == "__main__":
    debug_meta()
