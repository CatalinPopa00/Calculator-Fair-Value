import yfinance as yf
import json

def test_yf_search(query):
    print(f"\nTesting yfinance search for: '{query}'")
    try:
        # Some versions of yfinance might not have yf.Search
        # Let's try to use the underlying API that yfinance might be using
        import requests
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=20"
        res = requests.get(url, headers=headers).json()
        quotes = res.get('quotes', [])
        print(f"Results: {len(quotes)}")
        for q in quotes:
             print(f"{q.get('symbol')} - {q.get('quoteType')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_yf_search("m")
    test_yf_search("msft")
