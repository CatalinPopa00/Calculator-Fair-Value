import requests
import urllib.parse

def debug_search_q1(query):
    # Testing query1 host
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}&quotesCount=100&enableFuzzyQuery=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers)
    data = resp.json()
    quotes = data.get("quotes", [])
    print(f"\nQuery1 Results for '{query}' (Count: {len(quotes)}):")
    for q in quotes:
        symbol = q.get('symbol', '')
        q_type = q.get('quoteType', '')
        print(f"{symbol} - {q_type} - {q.get('shortname')}")

if __name__ == "__main__":
    debug_search_q1("m")
