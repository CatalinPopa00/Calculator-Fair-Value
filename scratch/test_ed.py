import yfinance as yf
ticker = "ADBE"
stock = yf.Ticker(ticker)
ed = stock.get_earnings_dates(limit=16)
print(f"Earnings Dates for {ticker}:")
print(ed)
if ed is not None and not ed.empty:
    print("Columns:", ed.columns)
