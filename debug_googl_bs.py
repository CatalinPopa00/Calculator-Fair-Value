import yfinance as yf
ticker = yf.Ticker("GOOGL")
bs = ticker.balance_sheet
if bs is not None and not bs.empty:
    print("Columns:", bs.columns)
    print("Index:", bs.index.tolist())
    print("\nLatest year data:")
    for idx in bs.index:
        print(f"{idx}: {bs.loc[idx].iloc[0]}")
else:
    print("Balance sheet not found.")
