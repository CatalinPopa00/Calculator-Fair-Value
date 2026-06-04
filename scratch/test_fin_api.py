import yfinance as yf
import sys

ticker = sys.argv[1]
t = yf.Ticker(ticker)

inc = t.income_stmt
if not inc.empty:
    print("\n--- INCOME STMT ROWS ---")
    for idx in inc.index: print(idx)

bs = t.balance_sheet
if not bs.empty:
    print("\n--- BALANCE SHEET ROWS ---")
    for idx in bs.index: print(idx)
