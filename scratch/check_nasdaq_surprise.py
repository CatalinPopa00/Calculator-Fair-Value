
import urllib.request
import json
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def get_nasdaq_surprise(ticker):
    url = f'https://api.nasdaq.com/api/company/{ticker}/earnings-surprise'
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=7) as response:
        data = json.loads(response.read())
        rows = data.get('data', {}).get('earningsSurpriseTable', {}).get('rows', [])
        print(f"Ticker: {ticker}")
        print(f"Total rows in surprise table: {len(rows)}")
        for row in rows[:8]: # Show last 8 quarters (2 years)
            print(row)

if __name__ == "__main__":
    get_nasdaq_surprise("ADBE")
    get_nasdaq_surprise("META")
