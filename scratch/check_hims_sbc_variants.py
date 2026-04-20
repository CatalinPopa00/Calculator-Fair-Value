
import yfinance as yf
ticker = yf.Ticker("HIMS")
cf = ticker.cashflow
print("Cashflow Index:")
print(cf.index.tolist())
idx = [i for i in cf.index if "stock" in i.lower()]
print(f"SBC Matching Indices: {idx}")
for i in idx:
    print(f"Row {i}:")
    print(cf.loc[i])
