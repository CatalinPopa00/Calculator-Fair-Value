import requests
import json

def debug_raw(query):
    url = f'https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=20'
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers)
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    debug_raw('AAPL')
