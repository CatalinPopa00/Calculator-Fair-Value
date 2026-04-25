import requests
ticker = "ADBE"
url = f"https://query2.finance.yahoo.com/v7/finance/quoteSummary/{ticker}?modules=earningsTrend"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers)
print(f"API Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(data)
