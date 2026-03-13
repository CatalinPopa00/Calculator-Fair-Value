import yfinance as yf
msft = yf.Ticker("MSFT")
aapl = yf.Ticker("AAPL")
print("MSFT debtToEquity:", msft.info.get('debtToEquity'))
print("AAPL debtToEquity:", aapl.info.get('debtToEquity'))
print("MSFT totalDebt:", msft.info.get('totalDebt'))
print("MSFT totalStockholderEquity:", msft.info.get('totalStockholderEquity'))
