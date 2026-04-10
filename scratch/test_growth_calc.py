
import sys
import os

# Add the directory to sys.path to import our module
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d')

from api.scraper.yahoo import get_nasdaq_earnings_growth

if __name__ == "__main__":
    ticker = "ADBE"
    # Using a typical ADBE trailing EPS for testing
    trailing_eps = 16.0
    growth = get_nasdaq_earnings_growth(ticker, trailing_eps)
    print(f"Ticker: {ticker}")
    print(f"Trailing EPS (YF fallback): {trailing_eps}")
    print(f"Calculated Growth (Arithmetic Mean): {growth}")
    if growth:
        print(f"Growth Percentage: {growth * 100:.2f}%")
