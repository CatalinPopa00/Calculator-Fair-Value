import yfinance as yf
import sys

ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
print(f"Ticker: {ticker}")
stock = yf.Ticker(ticker)
info = stock.info
print(f"profitMargins: {info.get('profitMargins')}")
print(f"operatingMargins: {info.get('operatingMargins')}")
