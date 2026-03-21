import requests
import urllib.parse

def debug_search(query):
    # Testing enableEnhancedTrivialQuery
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}&quotesCount=100&newsCount=0&enableFuzzyQuery=true&enableEnhancedTrivialQuery=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers)
    data = resp.json()
    quotes = data.get("quotes", [])
    print(f"\nResults for '{query}' (Count: {len(quotes)}):")
    for q in quotes:
        symbol = q.get('symbol', '')
        q_type = q.get('quoteType', '')
        if q_type in ['EQUITY', 'ETF']:
             print(f"{symbol} - {q_type} - {q.get('shortname')}")

if __name__ == "__main__":
    debug_search("m")
    debug_search("ms")
