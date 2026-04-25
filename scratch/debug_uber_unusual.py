
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf

ticker = "UBER"
stock = yf.Ticker(ticker)
print(f"--- UNUSUAL ITEMS for {ticker} ---")
if 'Total Unusual Items' in stock.financials.index:
    print(stock.financials.loc['Total Unusual Items'])
