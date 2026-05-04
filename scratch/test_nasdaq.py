import requests
import json

def test_nasdaq_api(ticker):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://www.nasdaq.com',
        'Referer': f'https://www.nasdaq.com/market-activity/stocks/{ticker.lower()}/earnings-estimate',
    }
    
    # 1. Earnings Forecast
    url_earnings = f"https://api.nasdaq.com/api/analyst/{ticker.upper()}/earnings-forecast"
    print(f"Fetching Earnings: {url_earnings}")
    try:
        resp = requests.get(url_earnings, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print("Earnings Data keys:", data.keys())
            # Save for inspection
            with open("nasdaq_earnings.json", "w") as f:
                json.dump(data, f, indent=4)
        else:
            print("Failed to fetch earnings.")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Revenue Estimates
    url_revenue = f"https://api.nasdaq.com/api/company/{ticker.upper()}/revenue-estimates"
    print(f"\nFetching Revenue: {url_revenue}")
    try:
        resp = requests.get(url_revenue, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print("Revenue Data keys:", data.keys())
            # Save for inspection
            with open("nasdaq_revenue.json", "w") as f:
                json.dump(data, f, indent=4)
        else:
            print("Failed to fetch revenue.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_nasdaq_api("ABNB")
