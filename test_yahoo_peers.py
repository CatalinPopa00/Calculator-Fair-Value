import requests
import json

def test_yahoo_peers(ticker):
    print(f"Testing Yahoo peers for {ticker}...")
    try:
        url = f"https://query2.finance.yahoo.com/v6/finance/recommendationstickers/{ticker}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            result = data.get('finance', {}).get('result', [])
            if result:
                recommended = result[0].get('recommendedSymbols', [])
                tickers = [s.get('symbol') for s in recommended]
                print(f"Recommended tickers: {tickers}")
                return tickers
            else:
                print("No result found in JSON")
        else:
            print(f"Failed with status {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    return []

if __name__ == "__main__":
    test_yahoo_peers("AAPL")
    print("-" * 20)
    test_yahoo_peers("INTU")
    print("-" * 20)
    test_yahoo_peers("TSLA")
