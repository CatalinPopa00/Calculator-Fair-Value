import scraper.yahoo as sy
import yfinance as yf
sy._peer_info_cache.clear()
print(sy.fetch_peer_info('ADBE', yf.Tickers('ADBE'), None, {}, 1234))
