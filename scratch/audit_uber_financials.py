
import yfinance as yf
import pandas as pd

def audit_uber_raw():
    ticker = "UBER"
    s = yf.Ticker(ticker)
    f = s.income_stmt
    print("--- INCOME STATEMENT ROWS ---")
    print(f.index.tolist())
    print("\n--- 2025 DATA ---")
    if not f.empty:
        col = f.columns[0] # Usually 2024 or 2025
        print(f"Column: {col}")
        print(f.loc[:, col])
    
    # Check specifically for normalized income
    print("\n--- NORMALIZED METRICS ---")
    metrics = ['Net Income', 'Other Income Expense', 'Other Non Operating Income Expenses', 'Normalized Income', 'Total Unusual Items']
    for m in metrics:
        if m in f.index:
            print(f"{m}: {f.loc[m].iloc[0]}")

audit_uber_raw()
