import requests
import json
import yfinance as yf

ticker = "BKNG"
stock = yf.Ticker(ticker)
trailing_eps = stock.info.get('trailingEps')
print(f"YFinance Trailing EPS: {trailing_eps}")

url = f'https://api.nasdaq.com/api/analyst/{ticker.upper()}/earnings-forecast'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

response = requests.get(url, headers=headers, timeout=10)
if response.status_code == 200:
    data = response.json()
    rows = data.get('data', {}).get('yearlyForecast', {}).get('rows', [])
    print("\nNasdaq Yearly Forecast Rows:")
    for idx, row in enumerate(rows):
        print(f"Index {idx}: {row}")
        
    if rows:
        target_idx = min(len(rows) - 1, 3)
        target_row = rows[target_idx]
        fwd_eps_nasdaq = float(target_row.get('consensusEPSForecast', 0))
        print(f"\nTarget Index: {target_idx}")
        print(f"Target Fwd EPS: {fwd_eps_nasdaq}")
        
        years = target_idx + 1
        cagr = (fwd_eps_nasdaq / trailing_eps) ** (1 / years) - 1
        print(f"Calculated CAGR: {cagr:.4%} (over {years} years)")
else:
    print(f"Error: {response.status_code}")
