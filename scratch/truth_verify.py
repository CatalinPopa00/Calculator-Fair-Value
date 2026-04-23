import requests
import re

ticker = "META"
url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers)
html = response.text

# Try to find the 29.68 value
# Analysis page uses JSON payload inside script tags.
# We look for "yearAgoEps" and context.
matches = re.finditer(r'"yearAgoEps":\{"raw":([\d\.]+)', html)
results = []
for m in matches:
    results.append(m.group(1))

print(f"Found yearAgoEps values: {results}")

# Check if 29.68 is in there
if "29.68" in results:
    print("SUCCESS: Found 29.68 in Yahoo Analysis HTML!")
else:
    print("FAILURE: 29.68 not found. Listing all raw numbers...")
    # List numbers near 'earningsEstimate'
    ee_match = re.search(r'"earningsEstimate":\{(.*?)\}', html)
    if ee_match:
        print(f"Earnings Estimate segment: {ee_match.group(1)[:500]}")
