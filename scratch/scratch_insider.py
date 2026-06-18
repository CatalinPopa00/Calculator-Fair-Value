import yfinance as yf

stock = yf.Ticker("AAPL")
df = stock.insider_roster_holders
print(df.columns.tolist())
print(df.head(2))
