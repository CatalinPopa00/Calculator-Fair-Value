
import yfinance as yf
import pandas as pd
import json

ticker = "UBER"
stock = yf.Ticker(ticker)

print(f"--- {ticker} EPS Source Audit ---")

# 1. info
info = stock.info
print(f"trailingEps: {info.get('trailingEps')}")
print(f"trailingNormalizedEps: {info.get('trailingNormalizedEps')}")

# 2. earnings_history
try:
    eh = stock.earnings_history
    print("\nearnings_history (Analyst Chart):")
    print(eh[['epsActual', 'epsEstimate', 'epsSurprisePct']].head(8))
except Exception as e:
    print(f"Error fetching earnings_history: {e}")

# 3. get_earnings_dates
try:
    ed = stock.get_earnings_dates(limit=8)
    print("\nearnings_dates (Earnings Calendar):")
    print(ed.head(8))
except Exception as e:
    print(f"Error fetching earnings_dates: {e}")

# 4. financials
try:
    fin = stock.financials
    if not fin.empty:
        idx = [i for i in fin.index if 'EPS' in str(i)]
        print("\nfinancials (GAAP):")
        print(fin.loc[idx])
except Exception as e:
    print(f"Error fetching financials: {e}")
