
import requests
import json

def check_nasdaq_yearly():
    ticker = "UBER"
    # Try the Nasdaq Yearly Earnings URL
    url = f"https://api.nasdaq.com/api/analyst/{ticker}/earnings-forecast"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

check_nasdaq_yearly()
