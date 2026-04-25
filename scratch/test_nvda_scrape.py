import requests
url = "https://finance.yahoo.com/quote/NVDA/analysis"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
r = requests.get(url, headers=headers)
print(f"NVDA Status: {r.status_code}")
print(f"NVDA root.App.main found: {'root.App.main' in r.text}")
print(f"NVDA yearAgoEps found: {'yearAgoEps' in r.text}")
