import yfinance as yf
ticker = 'NVO'
stock = yf.Ticker(ticker)
info = stock.info
print(f"Ticker: {ticker}")
print(f"Currency: {info.get('currency')}")
print(f"Financial Currency: {info.get('financialCurrency')}")
print(f"Trailing EPS: {info.get('trailingEps')}")
print(f"Forward EPS: {info.get('forwardEps')}")
print(f"Total Cash: {info.get('totalCash')}")
print(f"Total Revenue: {info.get('totalRevenue')}")
