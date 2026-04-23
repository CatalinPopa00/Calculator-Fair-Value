
import yfinance as yf
import json

def get_eh():
    ticker = "UBER"
    s = yf.Ticker(ticker)
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earningsHistory"
    resp = s.session.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = resp.json()
    print(json.dumps(data, indent=2))

get_eh()
