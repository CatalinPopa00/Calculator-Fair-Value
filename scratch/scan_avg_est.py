import requests
import re

ticker = "ADBE"
url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
r = requests.get(url, headers=headers)
html = r.text

tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
for i, table in enumerate(tables):
    rows = re.findall(r'<tr.*?</tr>', table, re.DOTALL)
    for row in rows:
        clean_row = re.sub(r'<[^>]+>', ' ', row).strip()
        if 'Avg. Estimate' in clean_row:
             print(f"Table {i} - Row {clean_row}")
