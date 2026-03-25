
import requests
import json

headers = {'User-Agent': 'Mozilla/5.0'}
ticker = "PLTR"

# Test v7 quote
url_v7 = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
resp = requests.get(url_v7, headers=headers)
print("--- v7 Quote ---")
if resp.status_code == 200:
    res = resp.json().get('quoteResponse', {}).get('result', [])
    if res:
        q = res[0]
        print(f"operatingMargins: {q.get('operatingMargins')}")
        # check other margin fields
        print(f"profitMargins: {q.get('profitMargins')}")

# Test v11 summary
url_v11 = f"https://query2.finance.yahoo.com/v11/finance/quoteSummary/{ticker}?modules=financialData,defaultKeyStatistics"
resp = requests.get(url_v11, headers=headers)
print("\n--- v11 Summary ---")
if resp.status_code == 200:
    res = resp.json().get('quoteSummary', {}).get('result', [{}])[0]
    fd = res.get('financialData', {})
    print(f"financialData -> operatingMargins: {fd.get('operatingMargins', {}).get('raw')}")
    print(f"financialData -> revenueGrowth: {fd.get('revenueGrowth', {}).get('raw')}")
    print(f"financialData -> freeCashflow: {fd.get('freeCashflow', {}).get('raw')}")
    
    stats = res.get('defaultKeyStatistics', {})
    print(f"stats -> earningsGrowth: {stats.get('earningsGrowth', {}).get('raw')}")
