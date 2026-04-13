import sys
import os

# Add current dir to path so we can import api
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_lightweight_company_data
import json

def test():
    tickers = ["LLY", "JNJ", "PFE"]
    results = {}
    for t in tickers:
        print(f"Testing {t}...")
        data = get_lightweight_company_data(t)
        results[t] = data
    
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    test()
