import yfinance as yf
import json

def test_trend(ticker):
    stock = yf.Ticker(ticker)
    # yfinance 0.2.x uses internal session
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earningsTrend"
    # Try with stock.session which has cookies
    r = stock.session.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    if r.status_code == 200:
        data = r.json()
        trends = data.get('quoteSummary', {}).get('result', [{}])[0].get('earningsTrend', {}).get('trend', [])
        return trends
    return f"Error: {r.status_code}"

print(json.dumps(test_trend('MSFT'), indent=2))
