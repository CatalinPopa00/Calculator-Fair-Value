import requests
import json
import time

def test_batch():
    tickers = ["LLY", "JNJ", "PFE", "MRK"]
    url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={','.join(tickers)}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    print(f"Testing URL: {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('quoteResponse', {}).get('result', [])
            print(f"Results Count: {len(results)}")
            for q in results:
                print(f"Ticker: {q.get('symbol')}, Name: {q.get('shortName')}, Price: {q.get('regularMarketPrice')}, PE: {q.get('trailingPE')}")
        else:
            print(f"Error Body: {resp.text[:500]}")
            
        print("\n--- Testing Single Endpoint (v11 QuoteSummary) ---")
        url_v11 = f"https://query2.finance.yahoo.com/v11/finance/quoteSummary/LLY?modules=assetProfile,financialData"
        resp_v11 = requests.get(url_v11, headers=headers, timeout=10)
        print(f"v11 Status: {resp_v11.status_code}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_batch()
