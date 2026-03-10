import yfinance as yf
import json

stock = yf.Ticker('SYF')
info = stock.info

print("--- INFO KEYS ---")
print([k for k in info.keys() if 'margin' in k.lower() or 'ratio' in k.lower() or 'debt' in k.lower() or 'cash' in k.lower()])

print("\n--- INFO VALUES ---")
print("freeCashflow:", info.get('freeCashflow'))
print("operatingCashflow:", info.get('operatingCashflow'))
print("debtToEquity:", info.get('debtToEquity'))
print("totalDebt:", info.get('totalDebt'))
print("totalCash:", info.get('totalCash'))
print("currentRatio:", info.get('currentRatio'))
print("ebitdaMargins:", info.get('ebitdaMargins'))

print("\n--- CASH FLOW ---")
cf = stock.cash_flow
if cf is not None and not cf.empty:
    print(cf.index.tolist())

print("\n--- BALANCE SHEET ---")
bs = stock.balance_sheet
if bs is not None and not bs.empty:
    print(bs.index.tolist())
