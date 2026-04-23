
import urllib.request
import json
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def get_nasdaq_earnings_surprise(ticker_symbol: str) -> list:
    try:
        url = f"https://api.nasdaq.com/api/company/{ticker_symbol.upper()}/earnings-surprise"
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.nasdaq.com',
            'Referer': 'https://www.nasdaq.com/'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            rows = data.get('data', {}).get('earningsSurpriseTable', {}).get('rows', [])
            return rows
    except Exception as e:
        print(f"Nasdaq check failed: {e}")
        return []

ticker = "UBER"
res = get_nasdaq_earnings_surprise(ticker)
print(f"\n--- Nasdaq Earnings Surprise for {ticker} ---")
for row in res[:8]:
    print(row)
