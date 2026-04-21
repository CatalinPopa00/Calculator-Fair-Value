import yfinance as yf
ticker = yf.Ticker("ADBE")
print(ticker.financials.columns)
