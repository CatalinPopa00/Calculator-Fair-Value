import requests
import re

ticker = "ADBE"
url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
r = requests.get(url, headers=headers)
html = r.text

# Find index of 20.94
idx = html.find('20.94')
if idx != -1:
    print(f"20.94 found at index {idx}")
    print("Context:")
    print(html[idx-200:idx+200])
else:
    print("20.94 not found")
