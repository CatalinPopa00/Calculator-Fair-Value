
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf

ticker = "UBER"
stock = yf.Ticker(ticker)
eh = stock.get_earnings_history(limit=20)

print(f"--- EARNINGS HISTORY (limit=20) for {ticker} ---")
print(eh)
