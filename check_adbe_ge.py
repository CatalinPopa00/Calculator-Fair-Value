import yfinance as yf
ticker = "ADBE"
stock = yf.Ticker(ticker)
print(stock.growth_estimates)
