
import requests
import json
import yfinance as yf

ticker = "MRK"
headers = {'User-Agent': 'Mozilla/5.0'}

# 1. Check yfinance info keys
print(f"--- yfinance info for {ticker} ---")
stock = yf.Ticker(ticker)
info = stock.info
growth_keys = [k for k in info.keys() if 'Growth' in k]
print(f"Growth keys found: {growth_keys}")
for k in growth_keys:
    print(f"{k}: {info.get(k)}")

# 2. Check v11 summary modules
url = f"https://query2.finance.yahoo.com/v11/finance/quoteSummary/{ticker}?modules=financialData,defaultKeyStatistics"
resp = requests.get(url, headers=headers)
print(f"\n--- v11 Summary for {ticker} ---")
if resp.status_code == 200:
    res = resp.json().get('quoteSummary', {}).get('result', [{}])[0]
    fd = res.get('financialData', {})
    stats = res.get('defaultKeyStatistics', {})
    
    print("FinancialData keys:", [k for k in fd.keys() if 'Growth' in k])
    print("DefaultKeyStats keys:", [k for k in stats.keys() if 'Growth' in k])
    
    # Check specific suspected keys
    print(f"financialData -> revenueGrowth: {fd.get('revenueGrowth')}")
    print(f"defaultKeyStatistics -> earningsGrowth: {stats.get('earningsGrowth')}")
