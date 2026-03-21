import requests
import urllib.parse

def debug_search_final(query):
    params = {
        'q': query,
        'quotesCount': 20,
        'newsCount': 0,
        'listsCount': 0,
        'enableFuzzyQuery': 'false',
        'quotesQueryId': 'pc_quote_search_query',
        'multiQuoteQueryId': 'pc_multi_quote_search_query',
        'enableEnhancedTrivialQuery': 'true',
        'region': 'US',
        'lang': 'en-US'
    }
    url = f"https://query1.finance.yahoo.com/v1/finance/search?{urllib.parse.urlencode(params)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://finance.yahoo.com/",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = requests.get(url, headers=headers)
    data = resp.json()
    quotes = data.get("quotes", [])
    print(f"\nFinal Test Results for '{query}' (Count: {len(quotes)}):")
    for q in quotes:
        print(f"{q.get('symbol')} - {q.get('quoteType')} - {q.get('shortname')}")

if __name__ == "__main__":
    debug_search_final("m")
