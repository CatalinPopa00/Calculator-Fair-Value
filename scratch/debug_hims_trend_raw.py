
import requests
import json
import random

def get_random_agent():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    return random.choice(agents)

ticker = "HIMS"
url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earningsTrend"
headers = {'User-Agent': get_random_agent()}
try:
    resp = requests.get(url, headers=headers).json()
    result = resp.get('quoteSummary', {}).get('result', [{}])[0].get('earningsTrend', {}).get('trend', [])
    for item in result:
        print(f"\nPeriod: {item.get('period')}")
        print(f"  Year Ago EPS: {item.get('yearAgoEps', {}).get('raw')}")
        print(f"  Actual: {item.get('earningsEstimate', {}).get('actual', {}).get('raw')}")
        print(f"  Avg Estimate: {item.get('earningsEstimate', {}).get('avg', {}).get('raw')}")
except Exception as e:
    print(f"Error: {e}")
