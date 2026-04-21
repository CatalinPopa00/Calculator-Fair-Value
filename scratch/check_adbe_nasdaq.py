
import requests
import json
import datetime

def get_random_agent():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def get_nasdaq_earnings_surprise(ticker):
    try:
        url = f"https://api.nasdaq.com/api/company/{ticker.upper()}/earnings-surprise"
        headers = {
            'User-Agent': get_random_agent(),
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://www.nasdaq.com',
            'Referer': 'https://www.nasdaq.com/'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('data', {}).get('earningsSurpriseTable', {}).get('rows', [])
    except Exception as e:
        print(f"Error: {e}")
    return []

ticker = "ADBE"
rows = get_nasdaq_earnings_surprise(ticker)
print(f"Nasdaq Rows for {ticker}: {len(rows)}")
for r in rows:
    print(r)
