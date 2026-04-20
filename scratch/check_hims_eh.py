
import yfinance as yf
import pandas as pd

ticker = yf.Ticker("HIMS")
eh = ticker.earnings_history
print("HIMS Earnings History:")
print(eh)
