import requests
ticker = "ADBE"
url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
r = requests.get(url, headers=headers)
print(f"Status: {r.status_code}")
print(f"Year Ago 20.94 found: {'20.94' in r.text}")
if '20.94' not in r.text:
    print(f"Page Title: {r.text[:500]}")
