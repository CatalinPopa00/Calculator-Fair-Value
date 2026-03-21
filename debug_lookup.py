import requests
import urllib.parse

def debug_lookup(query):
    # Testing lookup endpoint
    url = f"https://query2.finance.yahoo.com/v1/finance/lookup?q={urllib.parse.quote(query)}&quotesCount=20"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers)
    try:
        data = resp.json()
        print(f"\nLookup results for '{query}':")
        # Structure might be different
        print(json.dumps(data, indent=2)[:500])
    except Exception as e:
        print(f"Error: {e}")
        print(resp.text[:200])

if __name__ == "__main__":
    import json
    debug_lookup("m")
