
import yfinance as yf
import json

def debug_uber_json():
    ticker = "UBER"
    s = yf.Ticker(ticker)
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earningsTrend"
    resp = s.session.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = resp.json()
    print(json.dumps(data, indent=2))

debug_uber_json()
