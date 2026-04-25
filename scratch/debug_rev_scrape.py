
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

# Try to find the revenueEstimate block
match_rev_0y = re.search(r'\{"period":"0[yY]".*?"revenueEstimate":\{"avg":\{"raw":([\d\.\-eE]+).*?"yearAgoRevenue":\{"raw":([\d\.\-eE]+)', html)
if match_rev_0y:
    print(f"0y Revenue Avg: {match_rev_0y.group(1)}")
    print(f"0y Revenue Year Ago: {match_rev_0y.group(2)}")

match_rev_1y = re.search(r'\{"period":"\+1[yY]".*?"revenueEstimate":\{"avg":\{"raw":([\d\.\-eE]+)', html)
if match_rev_1y:
    print(f"+1y Revenue Avg: {match_rev_1y.group(1)}")

# Print a chunk of HTML around revenueEstimate for debugging if not found
if not match_rev_0y:
    idx = html.find("revenueEstimate")
    if idx != -1:
        print("\nDEBUG HTML:")
        print(html[idx:idx+1000])
