import requests
import re
import json

ticker = "ABNB"
url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
headers = {'User-Agent': "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}

response = requests.get(url, headers=headers)
html = response.text

for trend_key in ["revenueTrend", "earningsTrend", "earningsTrendNonGaap"]:
    print(f"\n--- {trend_key} ---")
    parts = html.split(f'"{trend_key}"')
    if len(parts) < 2: parts = html.split(f'\\"{trend_key}\\"')
    if len(parts) >= 2:
        chunk = parts[1][:5000]
        print(chunk)
    else:
        print("NOT FOUND")
