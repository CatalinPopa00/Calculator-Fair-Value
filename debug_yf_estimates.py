import yfinance as yf
import pandas as pd

ticker = "AAPL"
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

info = stock.info
print("\n--- Info Keys ---")
print(f"fiscalYearEnd: {info.get('fiscalYearEnd')}")
print(f"mostRecentQuarter: {info.get('mostRecentQuarter')}")
print(f"lastFiscalYearEnd: {info.get('lastFiscalYearEnd')}")
print(f"nextFiscalYearEnd: {info.get('nextFiscalYearEnd')}")
