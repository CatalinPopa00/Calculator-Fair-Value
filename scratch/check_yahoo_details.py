import requests
import json

ticker = "HIMS"
url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earningsTrend,earnings"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
data = resp.json()
print(json.dumps(data, indent=2))
