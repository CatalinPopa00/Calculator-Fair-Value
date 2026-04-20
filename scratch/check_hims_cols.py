
import yfinance as yf
ticker = yf.Ticker("HIMS")
print("Financials Cols:")
print(list(ticker.financials.columns))
print("Cashflow Cols:")
print(list(ticker.cashflow.columns))
