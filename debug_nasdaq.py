import urllib.request
import json
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def get_nasdaq_data(ticker):
    url = f'https://api.nasdaq.com/api/analyst/{ticker.upper()}/earnings-forecast'
    req = urllib.request.Request(url, headers={'User-Agent': random.choice(USER_AGENTS)})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())

try:
    data = get_nasdaq_data("AAPL")
    rows = data.get('data', {}).get('yearlyForecast', {}).get('rows', [])
    for i, r in enumerate(rows):
        print(f"Row {i}: {r}")
except Exception as e:
    print(f"Error: {e}")
