import sys
import os
import yfinance as yf

# Add the current directory to sys.path to allow imports from api
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_nasdaq_earnings_growth, get_company_data

def test_nike():
    ticker = "NKE"
    print(f"--- Fetching data for {ticker} ---")
    
    # Get trailing EPS first as it's a required parameter for the growth function
    stock = yf.Ticker(ticker)
    info = stock.info
    trailing_eps = info.get('trailingEps', 0)
    print(f"Trailing EPS (YF): {trailing_eps}")
    
    growth = get_nasdaq_earnings_growth(ticker, trailing_eps)
    if growth is not None:
        print(f"Nasdaq 3Y EPS Growth CAGR: {growth:.2%}")
    else:
        print("Nasdaq 3Y EPS Growth: Not found")

    # Also get full company data to see what the final selected growth is
    data = get_company_data(ticker)
    print(f"Selected EPS Growth: {data.get('eps_growth', 0):.2%}")
    print(f"Growth Period Source: {data.get('eps_growth_period', 'N/A')}")

if __name__ == "__main__":
    test_nike()
