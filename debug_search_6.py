import requests
import urllib.parse

def debug_search_6(query):
    # Testing quotesCount=6
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}&quotesCount=6"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers)
    data = resp.json()
    quotes = data.get("quotes", [])
    print(f"\nQuotesCount=6 Results for '{query}' (Count: {len(quotes)}):")
    for q in quotes:
        print(f"{q.get('symbol')} - {q.get('quoteType')} - {q.get('shortname')}")

if __name__ == "__main__":
    debug_search_6("m")
