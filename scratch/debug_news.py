import yfinance as yf
import json
news = yf.Ticker('AAPL').news
with open('scratch/debug_news.json', 'w', encoding='utf-8') as f:
    json.dump(news, f, indent=2)
