import requests
import re

ticker = "ADBE"
url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
r = requests.get(url, headers=headers)
html = r.text

# Find all tables
tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
for i, table in enumerate(tables):
    if '20.94' in table:
        print(f"Table {i} contains 20.94")
        # Extract rows
        rows = re.findall(r'<tr.*?</tr>', table, re.DOTALL)
        for row in rows:
            if '20.94' in row:
                # Clean row for printing
                clean_row = re.sub(r'<[^>]+>', ' ', row).strip()
                print(f"Row with 20.94: {clean_row}")
            if 'Avg. Estimate' in row:
                clean_row = re.sub(r'<[^>]+>', ' ', row).strip()
                print(f"Row with Avg. Est: {clean_row}")
