import requests
import urllib.parse

def debug_search(query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}&quotesCount=100&enableFuzzyQuery=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers)
    data = resp.json()
    quotes = data.get("quotes", [])
    print(f"\nResults for '{query}' (Count: {len(quotes)}):")
    found = False
    for q in quotes:
        symbol = q.get('symbol', '')
        if symbol in ['MSFT', 'META', 'AAPL', 'AMZN']:
            print(f"FOUND: {symbol} - {q.get('quoteType')} - {q.get('shortname')}")
            found = True
    
    if not found:
        print("Mega-caps NOT found in top 100.")
    
    # Print first 20 EQUITY/ETF results
    printed = 0
    for q in quotes:
        if q.get('quoteType') in ['EQUITY', 'ETF'] and '.' not in q.get('symbol', ''):
            print(f"{q.get('symbol')} - {q.get('shortname')}")
            printed += 1
            if printed >= 20:
                break

if __name__ == "__main__":
    debug_search("m")
    debug_search("a")
