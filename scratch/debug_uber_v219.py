
from scraper.yahoo import get_company_data
import json

def debug_uber_growth():
    print("Fetching UBER data...")
    data = get_company_data("UBER", fast_mode=False)
    
    print(f"Name: {data.get('name')}")
    print(f"EPS Growth (from dict): {data.get('eps_growth')}")
    print(f"EPS Growth Period: {data.get('eps_growth_period')}")
    
    print("\nProjections in historical_trends:")
    trends = data.get('historical_trends', [])
    for t in trends:
        if "Est" in str(t.get('year')):
            print(f"  {t.get('year')}: EPS={t.get('eps')}, Growth={t.get('eps_growth')}")

if __name__ == "__main__":
    debug_uber_growth()
