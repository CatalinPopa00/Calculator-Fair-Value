import yfinance as yf
ticker = yf.Ticker("GOOGL")
bs = ticker.balance_sheet
debt_keys = [idx for idx in bs.index if 'Debt' in str(idx) or 'Term Debt' in str(idx) or 'Liabilities' in str(idx)]
for col in bs.columns:
    print(f"\n--- {col} ---")
    for key in debt_keys:
        print(f"{key}: {bs.loc[key, col]}")
