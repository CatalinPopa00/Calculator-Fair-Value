
import requests
import re
import json

def get_random_agent():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

ticker = "NVDA"
url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
headers = {'User-Agent': get_random_agent()}
response = requests.get(url, headers=headers, timeout=10)
html = response.text

print(f"HTML Length: {len(html)}")
# Search for any numbers that look like revenue (e.g. billions)
matches = re.findall(r'"raw":([\d\.\-eE]+)', html)
print(f"Found {len(matches)} raw values")
if matches:
    print(f"First 10 values: {matches[:10]}")

# Search for the period keys
periods = re.findall(r'"period":"(.*?)"', html)
print(f"Found periods: {set(periods)}")
