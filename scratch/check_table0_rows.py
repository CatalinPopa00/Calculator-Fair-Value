import requests
import re

ticker = "ADBE"
url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
r = requests.get(url, headers=headers)
html = r.text

tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
rows = re.findall(r'<tr.*?</tr>', tables[0], re.DOTALL)
for row in rows:
    print(f"Table 0 Row: {re.sub(r'<[^>]+>', ' ', row).strip()}")
