import yfinance as yf
import pandas as pd

ticker = "AAPL"
stock = yf.Ticker(ticker)

print("--- info.get('earningsGrowth') ---")
print(stock.info.get('earningsGrowth'))

print("\n--- growth_estimates ---")
try:
    print(stock.growth_estimates)
except Exception as e:
    print(f"Error: {e}")

print("\n--- earnings_estimate ---")
try:
    print(stock.earnings_estimate)
except Exception as e:
    print(f"Error: {e}")
