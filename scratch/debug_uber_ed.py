
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf
import pandas as pd

ticker = "UBER"
stock = yf.Ticker(ticker)
ed = stock.get_earnings_dates(limit=20)

print(f"--- EARNINGS DATES (limit=20) for {ticker} ---")
print(ed)
