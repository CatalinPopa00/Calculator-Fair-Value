import requests
import json

def test_nasdaq_variations(ticker):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://www.nasdaq.com',
        'Referer': f'https://www.nasdaq.com/market-activity/stocks/{ticker.lower()}/revenue-estimates',
    }
    
    variations = [
        f"https://api.nasdaq.com/api/analyst/{ticker.upper()}/revenue-estimates",
        f"https://api.nasdaq.com/api/company/{ticker.upper()}/revenue-estimates",
        f"https://api.nasdaq.com/api/company/{ticker.upper()}/analyst-revenue-estimates",
        f"https://api.nasdaq.com/api/analyst/{ticker.upper()}/earnings-forecast", # Already works
    ]
    
    for url in variations:
        print(f"Trying: {url}")
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print("SUCCESS!")
                with open(f"nasdaq_{url.split('/')[-1]}.json", "w") as f:
                    json.dump(resp.json(), f, indent=4)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_nasdaq_variations("ABNB")
