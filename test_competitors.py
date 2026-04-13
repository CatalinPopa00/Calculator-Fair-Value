import os
import requests
import yfinance as yf
import pandas as pd
from api.scraper.yahoo import get_competitors_data

def test_competitors(ticker):
    print(f"Testing competitors for {ticker}...")
    # Check if API key is in environment
    api_key = os.environ.get('FINNHUB_API_KEY')
    print(f"FINNHUB_API_KEY present: {bool(api_key)}")
    
    # Try calling directly if we want to debug the API
    if api_key:
        try:
            url = f"https://finnhub.io/api/v1/stock/peers?symbol={ticker}&token={api_key}"
            resp = requests.get(url, timeout=10)
            print(f"Raw Finnhub status: {resp.status_code}")
            print(f"Raw Finnhub data: {resp.text}")
        except Exception as e:
            print(f"Direct API call failed: {e}")

    # Call the actual function
    peers = get_competitors_data(ticker, "Technology", "Software", limit=5)
    print(f"Final peers found: {peers}")

if __name__ == "__main__":
    test_ticker = "AAPL"
    test_competitors(test_ticker)
