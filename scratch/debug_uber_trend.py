
import urllib.request
import json
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def check_uber_trend():
    ticker = "UBER"
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earningsTrend"
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            trends = data['quoteSummary']['result'][0]['earningsTrend']['trend']
            print(f"--- {ticker} Earnings Trend ---")
            for t in trends:
                period = t.get('period')
                year_ago = t.get('growth', {}).get('yearAgoEps', {}).get('raw')
                print(f"Period: {period}, Year Ago EPS: {year_ago}")
    except Exception as e:
        print(f"Error: {e}")

check_uber_trend()
