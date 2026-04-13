from api.scraper.yahoo import get_nasdaq_earnings_growth
import yfinance as yf

ticker = "AAPL"
stock = yf.Ticker(ticker)
info = stock.info
trailing_eps = info.get('trailingEps')

print(f"Ticker: {ticker}")
print(f"Trailing EPS: {trailing_eps}")

cagr = get_nasdaq_earnings_growth(ticker, trailing_eps)
if cagr:
    print(f"Nasdaq 3Y Forward CAGR: {cagr:.2%}")
else:
    print("Could not fetch Nasdaq growth.")
