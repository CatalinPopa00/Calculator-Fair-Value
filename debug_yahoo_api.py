import requests
import json

def get_yahoo_trend(ticker):
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earningsTrend"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return f"Error: {response.status_code}"

ticker = "AAPL"
data = get_yahoo_trend(ticker)
print(json.dumps(data, indent=2))
