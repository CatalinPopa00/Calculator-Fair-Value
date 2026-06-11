import yfinance as yf
import json

ticker = yf.Ticker("AAPL")
news = ticker.news
if news:
    print(json.dumps(news[0], indent=2, default=str))
else:
    print("No news found")
