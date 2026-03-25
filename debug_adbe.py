
import sys
import os
import yfinance as yf

# Find the project root
root = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d"
sys.path.append(root)

from api.scraper.yahoo import get_company_data

ticker = "ADBE"
try:
    data = get_company_data(ticker)
    print(f"--- DATA FOR {ticker} ---")
    print(f"Current Price: {data.get('current_price')}")
    print(f"Trailing EPS (GAAP): {data.get('trailing_eps')}")
    print(f"Adjusted EPS (Non-GAAP): {data.get('adjusted_eps')}")
    print(f"EPS Growth (Forecast): {data.get('eps_growth')}")
    
    # Check yfinance growth estimates directly
    stock = yf.Ticker(ticker)
    ge = stock.growth_estimates
    if ge is not None and not ge.empty:
        print("\n--- YFINANCE GROWTH ESTIMATES ---")
        print(ge)
    else:
        print("\nNo yfinance growth estimates found.")
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
