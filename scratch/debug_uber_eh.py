
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf
import pandas as pd

ticker = "UBER"
stock = yf.Ticker(ticker)
eh = stock.earnings_history

print(f"--- EARNINGS HISTORY for {ticker} ---")
print(eh)
