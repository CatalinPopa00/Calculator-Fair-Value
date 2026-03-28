
import sys
import os
import logging

# Set up logging
logging.basicConfig(level=logging.ERROR)
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_company_data

def test_ticker(ticker):
    print(f"Testing {ticker}...")
    try:
        data = get_company_data(ticker, fast_mode=False)
        if data:
            print(f"Name: {data.get('name')}")
            print(f"Price: {data.get('current_price')}")
            print(f"Trailing EPS: {data.get('trailing_eps')}")
            print(f"Sector: {data.get('sector')}")
            print(f"PE Ratio: {data.get('pe_ratio')}")
            print(f"Success!")
        else:
            print("FAILURE: Could not fetch data.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_ticker("SOFI")
