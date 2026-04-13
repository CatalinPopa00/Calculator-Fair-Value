
import requests
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

ticker = "GOOGL"
urls = [
    f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/{ticker}",
    f"https://query2.finance.yahoo.com/v6/finance/recommendationsforsymbol/{ticker}",
    f"https://query2.finance.yahoo.com/v11/finance/recommendationsforsymbol/{ticker}"
]

for url in urls:
    print(f"\nTesting: {url}")
    try:
        resp = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Data Sample: {resp.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
