import yfinance as yf
import pandas as pd

ticker = "ABNB"
stock = yf.Ticker(ticker)
financials = stock.financials

print(f"Financials Columns: {financials.columns}")
if 'Total Revenue' in financials.index:
    print(f"Total Revenue Index: {financials.index.get_loc('Total Revenue')}")
    print(f"Total Revenue Values:\n{financials.loc['Total Revenue']}")
else:
    print("Total Revenue NOT FOUND in financials.index")
    print(f"Available indices: {financials.index.tolist()}")

cashflow = stock.cashflow
if 'Free Cash Flow' in cashflow.index:
    print(f"Free Cash Flow Values:\n{cashflow.loc['Free Cash Flow']}")
else:
    print("Free Cash Flow NOT FOUND in cashflow.index")
