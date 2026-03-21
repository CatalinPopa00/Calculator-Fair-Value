import requests
import urllib.parse
import json

def get_random_agent():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def debug_search(query):
    url = f'https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}&quotesCount=20'
    headers = {'User-Agent': get_random_agent()}
    print(f"\n--- Debugging Query: {query} ---")
    resp = requests.get(url, headers=headers)
    data = resp.json()
    quotes = data.get('quotes', [])
    print(f"Total quotes returned: {len(quotes)}")
    for q in quotes:
        print(f"Symbol: {q.get('symbol')}, Type: {q.get('quoteType')}, Exch: {q.get('exchDisp')}")

if __name__ == "__main__":
    debug_search('m')
    debug_search('nvo')
    debug_search('aapl')
