
import yfinance as yf
import json

ticker = yf.Ticker("HIMS")
trend = ticker.earnings_trend
print("HIMS Earnings Trend:")
print(trend)
