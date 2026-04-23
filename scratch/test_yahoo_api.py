import requests
import json

def test_yahoo_api_modules(ticker):
    modules = ["earningsTrend", "earningsEstimate", "revenueEstimate"]
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules={','.join(modules)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    print(f"Fetching {url}...")
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        with open(f"{ticker}_api_response.json", "w") as f:
            json.dump(data, f, indent=2)
        
        result = data.get('quoteSummary', {}).get('result', [{}])[0]
        trends = result.get('earningsTrend', {}).get('trend', [])
        
        print(f"Found {len(trends)} periods in earningsTrend.")
        for t in trends:
            p = t.get('period')
            avg = t.get('earningsEstimate', {}).get('avg', {}).get('raw')
            yearAgo = t.get('earningsEstimate', {}).get('yearAgoEps', {}).get('raw')
            print(f"Period: {p}, Avg: {avg}, YearAgo: {yearAgo}")
    else:
        print(f"Error: {resp.status_code}")

if __name__ == "__main__":
    test_yahoo_api_modules("META")
