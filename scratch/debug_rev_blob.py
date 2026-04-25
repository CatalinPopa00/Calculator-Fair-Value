
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

print(f"--- SCRAPING REVENUE FOR {ticker} ---")

# Look for the JSON blob
match_json = re.search(r'root\.App\.main = (\{.*?\});', html)
if match_json:
    print("Found JSON blob")
    # Save a bit of it
    with open("c:\\Users\\Snoozie\\Downloads\\Calculator-Fair-Value\\scratch\\analysis_blob.json", "w") as f:
        f.write(match_json.group(1))
else:
    print("JSON blob not found. Trying simpler search.")
    idx = html.find("revenueEstimate")
    if idx != -1:
        print(f"Found revenueEstimate at index {idx}")
        print(html[idx:idx+1000])
    else:
        print("revenueEstimate not found in HTML.")
