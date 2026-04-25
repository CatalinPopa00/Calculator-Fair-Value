
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import requests
import json
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

ticker = "UBER"
url = f"https://api.nasdaq.com/api/company/{ticker.upper()}/earnings-surprise"
headers = {
    'User-Agent': random.choice(USER_AGENTS),
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://www.nasdaq.com',
    'Referer': 'https://www.nasdaq.com/'
}

resp = requests.get(url, headers=headers, timeout=10)
data = resp.json()
print(json.dumps(data, indent=2))
