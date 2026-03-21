import yfinance as yf

def check_quarters(ticker_symbol):
    print(f"Checking {ticker_symbol}...")
    ticker = yf.Ticker(ticker_symbol)
    
    try:
        q_inc = ticker.quarterly_income_stmt
        q_cf = ticker.quarterly_cashflow
        print(f"Income Stmt columns: {len(q_inc.columns)}")
        print(f"Cashflow columns: {len(q_cf.columns)}")
        common = set(q_inc.columns).intersection(q_cf.columns)
        print(f"Common columns: {len(common)}")
    except Exception as e:
        print(f"Basic financials failed: {e}")

    print("-" * 30)
    try:
        eh = ticker.earnings_history
        print(f"Earnings History rows: {len(eh)}")
        print(f"Columns: {eh.columns.tolist()}")
        print(eh.head(10))
    except Exception as e:
        print(f"earnings_history property failed: {e}")

if __name__ == "__main__":
    check_quarters("ADBE")
