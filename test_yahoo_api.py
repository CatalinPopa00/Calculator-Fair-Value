import requests
import json
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

def get_random_agent():
    return random.choice(USER_AGENTS)

def test_ticker(ticker_symbol):
    ticker_symbol = ticker_symbol.upper()
    url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker_symbol}"
    headers = {'User-Agent': get_random_agent()}
    print(f"Testing {ticker_symbol} via V7...")
    resp = requests.get(url, headers=headers, timeout=5)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json().get('quoteResponse', {}).get('result', [])
        if result:
            print(json.dumps(result[0], indent=2))
        else:
            print("No result in V7")
    
    print("-" * 20)
    url_v11 = f"https://query2.finance.yahoo.com/v11/finance/quoteSummary/{ticker_symbol}?modules=assetProfile,defaultKeyStatistics,financialData,summaryDetail"
    print(f"Testing {ticker_symbol} via V11...")
    resp_v11 = requests.get(url_v11, headers=headers, timeout=5)
    print(f"Status: {resp_v11.status_code}")
    if resp_v11.status_code == 200:
        print(json.dumps(resp_v11.json(), indent=2)[:2000] + "...")
    else:
        print(f"V11 Error: {resp_v11.text}")

if __name__ == "__main__":
    test_ticker("LLY")
