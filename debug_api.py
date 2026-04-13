
import requests
import json

ticker = "MRK"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x44) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

url = f"https://query2.finance.yahoo.com/v11/finance/quoteSummary/{ticker}?modules=financialData,defaultKeyStatistics"
resp = requests.get(url, headers=headers)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    res = data.get('quoteSummary', {}).get('result', [{}])[0]
    fd = res.get('financialData', {})
    stats = res.get('defaultKeyStatistics', {})
    
    print("\n[FinancialData Sample]")
    print(f"revenueGrowth: {fd.get('revenueGrowth')}")
    print(f"operatingMargins: {fd.get('operatingMargins')}")
    
    print("\n[DefaultKeyStats Sample]")
    print(f"earningsGrowth: {stats.get('earningsGrowth')}")
    print(f"trailingEps: {stats.get('trailingEps')}")
else:
    print(resp.text)
