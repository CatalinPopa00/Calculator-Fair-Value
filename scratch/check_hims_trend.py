import requests
import json

ticker = "HIMS"
url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earningsTrend"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
data = resp.json()
trends = data.get('quoteSummary', {}).get('result', [{}])[0].get('earningsTrend', {}).get('trend', [])

for t in trends:
    p = t.get('period')
    ya = t.get('earningsEstimate', {}).get('avg', {}).get('raw')
    # Actually, yearAgoEps is usually inside the estimate row if I recall
    # Let's print the whole trend entry for one period
    if p in ['0y', '+1y']:
        print(f"Period: {p}")
        print(json.dumps(t, indent=2))
