import yfinance as yf
inf = yf.Ticker('ADBE').info
print(inf.get('currency'), inf.get('exchange'))
