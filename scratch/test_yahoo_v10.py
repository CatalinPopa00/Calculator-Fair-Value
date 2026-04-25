import requests
ticker = "ADBE"
url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earningsTrend"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers)
print(f"API Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    trends = data.get('quoteSummary', {}).get('result', [{}])[0].get('earningsTrend', {}).get('trend', [])
    for t in trends:
        p = t.get('period')
        if p in ['0y', '+1y']:
            avg = t.get('earningsEstimate', {}).get('avg', {}).get('raw')
            ya = t.get('yearAgoEps', {}).get('raw')
            print(f"Period: {p}, Avg: {avg}, Year Ago: {ya}")
