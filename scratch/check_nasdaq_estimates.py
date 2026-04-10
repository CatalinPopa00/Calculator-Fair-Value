
import urllib.request
import json
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def get_nasdaq_estimates(ticker):
    url = f"https://api.nasdaq.com/api/analyst/{ticker}/estimates"
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept": "application/json"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read())
        print(f"--- Nasdaq Estimates for {ticker} ---")
        rows = data.get('data', {}).get('yearlyEpsForecast', [])
        for row in rows:
            print(row)

if __name__ == "__main__":
    get_nasdaq_estimates("META")
    get_nasdaq_estimates("ADBE")
