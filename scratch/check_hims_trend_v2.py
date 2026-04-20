import requests
import json

ticker = "HIMS"
url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earningsTrend"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
data = resp.json()
result = data.get('quoteSummary', {}).get('result')
if result:
    trends = result[0].get('earningsTrend', {}).get('trend', [])
    for t in trends:
        print(f"--- Period: {t.get('period')} ---")
        # print(json.dumps(t, indent=2)) 
        # Check for estimates
        est = t.get('earningsEstimate')
        if est:
            print(f"  Avg: {est.get('avg', {}).get('raw')}")
            print(f"  Year Ago: {t.get('earningsEstimate', {}).get('yearAgoEps', {}).get('raw')}")
else:
    print("No result found.")
