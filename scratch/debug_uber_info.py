
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf
import json

ticker = "UBER"
stock = yf.Ticker(ticker)
info = stock.info

print(f"--- INFO TAGS for {ticker} ---")
print(f"epsCurrentYear: {info.get('epsCurrentYear')}")
print(f"epsForward: {info.get('epsForward')}")
print(f"forwardEps: {info.get('forwardEps')}")
print(f"trailingEps: {info.get('trailingEps')}")

print("\n--- EARNINGS ESTIMATE TABLE ---")
print(stock.earnings_estimate)

print("\n--- GROWTH ESTIMATES ---")
print(stock.growth_estimates)
