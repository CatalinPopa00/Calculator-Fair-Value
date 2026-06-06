import yfinance as yf
inf = yf.Ticker('ADBE').info
print('regularMarketPrice:', inf.get('regularMarketPrice'), 'previousClose:', inf.get('previousClose'), 'open:', inf.get('open'))
