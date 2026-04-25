
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf

ticker = "UBER"
stock = yf.Ticker(ticker)
print(f"--- QUARTERLY FINANCIALS INDEX for {ticker} ---")
print(stock.quarterly_financials.index.tolist())

if 'Normalized Income' in stock.quarterly_financials.index:
    print("\nQuarterly Normalized Income:")
    print(stock.quarterly_financials.loc['Normalized Income'])
