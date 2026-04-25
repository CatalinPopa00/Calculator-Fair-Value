
import json
import sys
import os
sys.path.append(os.getcwd())

from scraper.yahoo import get_analyst_data
import yfinance as yf

ticker = "UBER"
stock = yf.Ticker(ticker)
info = stock.info

print(f"--- REFORMED ANALYST DATA FOR {ticker} ---")
data = get_analyst_data(stock, ticker, info)

print("\nEPS ESTIMATES:")
print(json.dumps(data.get('eps_estimates'), indent=2))

print("\nREVENUE ESTIMATES:")
print(json.dumps(data.get('rev_estimates'), indent=2))

print(f"\nEPS 5YR GROWTH: {data.get('eps_5yr_growth')}")
