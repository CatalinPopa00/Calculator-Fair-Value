from api.scraper.yahoo import get_nasdaq_earnings_growth, get_company_data
import yfinance as yf

ticker = "ADBE"
stock = yf.Ticker(ticker)
info = stock.info
trailing_eps = info.get('trailingEps')

print(f"Ticker: {ticker}")
print(f"Trailing EPS: {trailing_eps}")

# Nasdaq
cagr_nasdaq = get_nasdaq_earnings_growth(ticker, trailing_eps)

# Yahoo (main data)
data = get_company_data(ticker)
cagr_yahoo = data.get('eps_growth_5y_consensus')

print(f"\nNasdaq 3Y Forward CAGR: {cagr_nasdaq:.2%}" if cagr_nasdaq else "\nNasdaq 3Y Forward CAGR: N/A")
print(f"Yahoo 5Y Analyst Cons.: {cagr_yahoo:.2%}" if cagr_yahoo else "Yahoo 5Y Analyst Cons.: N/A")
