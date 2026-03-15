import requests
import json

def test_stockanalysis_peers(ticker):
    print(f"Testing StockAnalysis peers for {ticker}...")
    try:
        # Note: sometimes they need a specific User-Agent
        url = f"https://api.stockanalysis.com/wp-json/sa/v1/ticker/peers?symbol={ticker}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Data: {data}")
            return data
        else:
            print(f"Failed with status {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    return []

if __name__ == "__main__":
    test_stockanalysis_peers("AAPL")
    print("-" * 20)
    test_stockanalysis_peers("INTU")
