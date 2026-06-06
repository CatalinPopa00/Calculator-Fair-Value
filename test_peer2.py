import scraper.yahoo as sy
import yfinance as yf
sy._peer_info_cache.clear()
print(sy.get_competitors_data('NOW', 4, ['ADBE'], force_refresh=True))
