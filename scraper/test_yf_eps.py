import yfinance as yf
import json

stock = yf.Ticker("ADBE")
ed = stock.get_earnings_dates(limit=20)
print(ed)
