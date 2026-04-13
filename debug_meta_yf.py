import yfinance as yf
import datetime
import pandas as pd

ticker = "META"
stock = yf.Ticker(ticker)

print(f"--- {ticker} DEBUG ---")
print(f"Current Date: {datetime.datetime.now()}")

# Info
info = stock.info
print(f"Fiscal Year End Month: {info.get('fiscalYearEndMonth')}")
print(f"Last Fiscal Year End (timestamp): {info.get('lastFiscalYearEnd')}")
if info.get('lastFiscalYearEnd'):
    print(f"Last Fiscal Year End (date): {datetime.datetime.fromtimestamp(info.get('lastFiscalYearEnd'))}")

# Financials
if not stock.financials.empty:
    print(f"Financials Columns: {list(stock.financials.columns)}")
else:
    print("Financials empty")

# Estimates
if stock.earnings_estimate is not None:
    print("Earnings Estimates Index:")
    print(stock.earnings_estimate.index.tolist())
else:
    print("Earnings Estimates None")
