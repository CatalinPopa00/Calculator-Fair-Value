import requests
import re

ticker = "ADBE"
url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
r = requests.get(url, headers=headers)
html = r.text

tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
for i, table in enumerate(tables):
    # Get first 100 chars of table to see headers
    header_part = table[:500]
    print(f"Table {i} start: {re.sub(r'<[^>]+>', ' ', header_part).strip()}")
