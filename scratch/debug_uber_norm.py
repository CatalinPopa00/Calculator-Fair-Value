
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf

ticker = "UBER"
stock = yf.Ticker(ticker)
print(f"--- FINANCIALS INDEX for {ticker} ---")
print(stock.financials.index.tolist())

if 'Normalized Income' in stock.financials.index:
    print("\nNormalized Income:")
    print(stock.financials.loc['Normalized Income'])
