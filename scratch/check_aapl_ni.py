
import yfinance as yf
import pandas as pd

def find_idx(df, target):
    if df is None or df.empty: return None
    target_lower = str(target).lower().strip()
    for idx in df.index:
        if str(idx).lower().strip() == target_lower: return idx
    return None

ticker = "AAPL"
stock = yf.Ticker(ticker)
fin = stock.financials
print("Financials index:")
for i in fin.index:
    print(f"'{i}'")

target = "Net Income"
idx = find_idx(fin, target)
print(f"\nFound index for '{target}': {idx}")
if idx:
    print(f"Value for 2023: {fin.loc[idx].iloc[2]}") # 2023 is usually 3rd col
