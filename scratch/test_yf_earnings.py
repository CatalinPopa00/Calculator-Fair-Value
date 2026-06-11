import yfinance as yf

def explore_ticker(symbol):
    t = yf.Ticker(symbol)
    print(f"--- Income Statement (Yearly) for {symbol} ---")
    try:
        print(t.income_stmt.head(5))
        print("Columns (Years):", t.income_stmt.columns)
    except Exception as e:
        print("Error:", e)

explore_ticker('ADBE')
