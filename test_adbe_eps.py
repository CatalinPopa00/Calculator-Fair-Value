import sys
import os
import yfinance as yf
import urllib.request
import json

# Add the current directory to sys.path to allow imports from api
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_nasdaq_earnings_growth, get_company_data

def test_adobe():
    ticker = "ADBE"
    print(f"--- Fetching data for {ticker} ---")
    
    # 1. Get Trailing EPS (T0) from Yahoo
    stock = yf.Ticker(ticker)
    info = stock.info
    trailing_eps = info.get('trailingEps', 0)
    print(f"Trailing EPS (T0) from Yahoo: {trailing_eps}")
    
    # 2. Get Raw Nasdaq Forecast Rows (T1, T2, T3)
    try:
        url = f'https://api.nasdaq.com/api/analyst/{ticker.upper()}/earnings-forecast'
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
            rows = data.get('data', { }).get('yearlyForecast', { }).get('rows', [])
            print("\nNasdaq Yearly Forecast Rows:")
            for i, row in enumerate(rows[:3]):
                print(f"  T{i+1} ({row.get('fiscalYearEnd')}): {row.get('consensusEPSForecast')}")
    except Exception as e:
        print(f"Could not fetch raw Nasdaq rows: {e}")

    # 3. Calculate CAGR using the new logic in the scraper
    growth = get_nasdaq_earnings_growth(ticker, trailing_eps)
    if growth is not None:
        print(f"\nFinal Calculated CAGR (T0 -> T3): {growth:.2%}")
    else:
        print("\nCAGR Calculation failed")

    # 4. Check full company data
    print("\n--- Full Scraper Result ---")
    data = get_company_data(ticker)
    if data:
        print(f"EPS Growth: {data.get('eps_growth'):.2%}")
        print(f"Growth Period: {data.get('eps_growth_period')}")
    else:
        print("Scraper failed to return data")

if __name__ == "__main__":
    test_adobe()
