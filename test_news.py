import yfinance as yf
import json

stock = yf.Ticker("AAPL")
news = stock.news
if news:
    print(json.dumps(news[0], indent=2))
