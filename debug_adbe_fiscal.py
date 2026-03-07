import yfinance as yf
ticker = "ADBE"
stock = yf.Ticker(ticker)

print(f"--- {ticker} INFO ---")
print(f"Fiscal Year Ends: {stock.info.get('fiscalYearEnd')}")
print(f"Most Recent Quarter: {stock.info.get('mostRecentQuarter')}")

print("\n--- EARNINGS ESTIMATE ---")
try:
    ef = stock.earnings_estimate
    print(ef)
except Exception as e:
    print(e)
