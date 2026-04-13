import yfinance as yf
ticker = yf.Ticker("AAPL")
df = ticker.earnings_estimate
print(df)
