import yfinance as yf
import pandas as pd
import json

ticker = "HIMS"
stock = yf.Ticker(ticker)

print("--- Earnings Estimate ---")
try:
    print(stock.earnings_estimate)
except Exception as e:
    print(f"Error: {e}")

print("\n--- Revenue Estimate ---")
try:
    print(stock.revenue_estimate)
except Exception as e:
    print(f"Error: {e}")

print("\n--- Earnings History ---")
try:
    print(stock.earnings_history)
except Exception as e:
    print(f"Error: {e}")

print("\n--- Financials ---")
try:
    print(stock.financials.loc['Diluted EPS'])
except Exception as e:
    print(f"Error: {e}")

print("\n--- Info Highlights ---")
info = stock.info
for k in ['trailingEps', 'forwardEps', 'epsTrailingTwelveMonths', 'marketCap']:
    print(f"{k}: {info.get(k)}")

# Try to find Normalized EPS in info?
# Search for any key containing 'Normalized' or 'Adjusted'
adj_keys = [k for k in info.keys() if 'adj' in k.lower() or 'norm' in k.lower()]
print(f"\nAdjusted/Normalized keys in info: {adj_keys}")
for k in adj_keys:
    print(f"{k}: {info.get(k)}")
