import yfinance as yf
import time

stock = yf.Ticker("SMCI")

t0 = time.time()
fin = stock.financials
t1 = time.time()
print(f"Time for financials (first fetch): {t1 - t0:.2f}s")

t0 = time.time()
cf = stock.cashflow
bs = stock.balance_sheet
qbs = stock.quarterly_balance_sheet
t1 = time.time()
print(f"Time for remaining (cached): {t1 - t0:.2f}s")
