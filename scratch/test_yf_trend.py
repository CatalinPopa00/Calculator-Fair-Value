import yfinance as yf
ticker = "ADBE"
stock = yf.Ticker(ticker)
print(f"Earnings Trend for {ticker}:")
try:
    print(stock.earnings_trend)
except Exception as e:
    print(f"Error: {e}")
