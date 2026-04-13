import requests
import json

def debug_raw(query):
    url = f'https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=20'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    resp = requests.get(url, headers=headers)
    with open('yahoo_search_raw.json', 'w') as f:
        json.dump(resp.json(), f, indent=2)
    print(f"Status: {resp.status_code}")
    print("Saved to yahoo_search_raw.json")

if __name__ == "__main__":
    debug_raw('AAPL')
