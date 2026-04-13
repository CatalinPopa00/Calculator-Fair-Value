import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'api'))
from scraper.yahoo import get_company_data

def test_ticker(ticker):
    print(f"\nTesting {ticker}...")
    data = get_company_data(ticker)
    if data:
        print(f"Dividend Streak: {data.get('dividend_streak')} years")
        print(f"Dividend CAGR 5Y: {data.get('dividend_cagr_5y')}")
        print(f"Red Flags: {data.get('red_flags')}")
    else:
        print("Failed to fetch data.")

if __name__ == "__main__":
    test_ticker("KO")
    test_ticker("AAPL")
