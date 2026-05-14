import yfinance as yf
import json

ticker = "BKNGCL.SN"
stock = yf.Ticker(ticker)
print(f"Price: {stock.fast_info.get('last_price')}")
print(f"Info EPS: {stock.info.get('trailingEps')}")
print(f"Financials EPS: {stock.financials.loc['Diluted EPS'] if 'Diluted EPS' in stock.financials.index else 'N/A'}")
