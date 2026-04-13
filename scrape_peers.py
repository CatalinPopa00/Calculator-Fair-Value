import requests
import re

def scrape_yahoo_peers(ticker):
    print(f"Scraping Yahoo peers for {ticker}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        url = f"https://finance.yahoo.com/quote/{ticker}/"
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            # Look for tickers in the "Peers" section or related links
            # Usually they are in a specific JSON block or in links like /quote/TICKER/
            # Let's try to find symbols that appear multiple times or in a specific context
            
            # Simple heuristic: find all tickers in capital letters inside /quote/SYMBOL/
            matches = re.findall(r'/quote/([A-Z^.-]+)/', resp.text)
            # Filter out indices and common words, and the ticker itself
            ignore = {'GSPC', 'DJI', 'IXIC', 'RUT', 'TNX', 'VIX', ticker}
            peers = []
            for m in matches:
                if m not in ignore and len(m) <= 5 and m.isalpha():
                    if m not in peers:
                        peers.append(m)
            
            print(f"Found potential peers: {peers[:10]}")
            return peers[:5]
        else:
            print(f"Failed to fetch page: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    return []

if __name__ == "__main__":
    scrape_yahoo_peers("INTU")
    print("-" * 20)
    scrape_yahoo_peers("ADBE")
