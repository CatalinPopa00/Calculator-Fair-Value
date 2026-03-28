import yfinance as yf
import json
import os
import sys

# Add the project root to sys.path to import local modules
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_nasdaq_earnings_growth

def debug_sofi():
    ticker_symbol = "SOFI"
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    trailing_eps = info.get('trailingEps', 0.0)
    print(f"Ticker: {ticker_symbol}")
    print(f"Trailing EPS: {trailing_eps}")
    
    growth = get_nasdaq_earnings_growth(ticker_symbol, trailing_eps)
    print(f"Nasdaq Growth Estimate: {growth}")
    
    if growth is not None:
        print(f"Growth Percentage: {growth * 100:.2f}%")
    else:
        print("Growth is None")

    # Check PEG formula components
    current_price = info.get('currentPrice')
    eps_base = trailing_eps or 0
    current_pe = current_price / eps_base if eps_base > 0 else 0
    print(f"Current Price: {current_price}")
    print(f"Current P/E: {current_pe}")
    
    if growth and growth > 0:
        company_peg = current_pe / (growth * 100)
        print(f"Calculated PEG: {company_peg}")
    else:
        print("PEG cannot be calculated (growth <= 0 or None)")

if __name__ == "__main__":
    debug_sofi()
