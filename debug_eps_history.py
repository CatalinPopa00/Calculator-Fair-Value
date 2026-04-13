import yfinance as yf
ticker = "ADBE"
stock = yf.Ticker(ticker)
print(f"--- {ticker} EARNINGS HISTORY ---")
try:
    eh = stock.earnings_history
    print(eh)
    print("\nColumns:", eh.columns if hasattr(eh, 'columns') else "No columns")
    print("Index:", eh.index if hasattr(eh, 'index') else "No index")
except Exception as e:
    print(e)
