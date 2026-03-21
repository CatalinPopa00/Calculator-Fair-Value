import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'api'))
from scraper.yahoo import get_company_data

def test_ticker(ticker):
    print(f"\n--- Testing {ticker} ---")
    data = get_company_data(ticker)
    if data:
        print(f"Summary: {data.get('business_summary')}")
        print(f"Next Earnings: {data.get('next_earnings_date')}")
        print(f"Red Flags: {data.get('red_flags')}")
    else:
        print("Failed to fetch data.")

if __name__ == "__main__":
    test_ticker("KO")
    test_ticker("MSFT")
    test_ticker("AAPL")
