import yfinance as yf
import json
import urllib.request
import pandas as pd

def get_random_agent():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def safe_nasdaq_float(val):
    if val is None: return 0.0
    try:
        return float(str(val).replace('$', '').replace(',', '').strip())
    except: return 0.0

def get_nasdaq_comprehensive_estimates(ticker):
    ticker = ticker.upper()
    try:
        url = f'https://api.nasdaq.com/api/analyst/{ticker}/earnings-forecast'
        headers = {'User-Agent': get_random_agent()}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=7) as response:
            data = json.loads(response.read())
            return data.get('data', {}).get('yearlyForecast', {}).get('rows', [])
    except Exception as e:
        print(f"Error fetching Nasdaq: {e}")
        return []

ticker = 'NVO'
stock = yf.Ticker(ticker)
info = stock.info

trailing_eps_yf = info.get('trailingEps')
print(f"YF Trailing EPS: {trailing_eps_yf}")
print(f"YF Currency: {info.get('currency')}")
print(f"YF Financial Currency: {info.get('financialCurrency')}")

nasdaq_rows = get_nasdaq_comprehensive_estimates(ticker)
print("\nNasdaq Yearly Forecast:")
for row in nasdaq_rows:
    print(row)

if nasdaq_rows and trailing_eps_yf:
    base_eps = trailing_eps_yf
    target_idx = min(len(nasdaq_rows) - 1, 2)
    raw_val = nasdaq_rows[target_idx].get('consensusEPSForecast', 0)
    target_eps = safe_nasdaq_float(raw_val)
    n_years = target_idx + 1
    
    effective_base = max(base_eps, 0.10) if base_eps > 0 else base_eps
    cagr = (target_eps / effective_base) ** (1 / n_years) - 1
    print(f"\nCalculated CAGR: {cagr*100:.2f}%")
    print(f"Base (YF): {effective_base}, Target (NQ Year {n_years}): {target_eps}")
