import yfinance as yf
ticker = yf.Ticker("ADBE")
print("Annual Financials (Diluted EPS):")
try:
    print(ticker.financials.loc["Diluted EPS"])
except:
    print("Not found")

print("\nEarnings History (Actual):")
try:
    print(ticker.earnings_history['epsActual'])
except:
    print("Not found")
