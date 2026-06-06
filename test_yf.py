import yfinance as yf
inf = yf.Ticker('ADBE').info
print(inf.get('currentPrice'), inf.get('forwardEps'), inf.get('marketCap'))
