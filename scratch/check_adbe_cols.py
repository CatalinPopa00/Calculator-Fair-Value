import yfinance as yf
ticker = yf.Ticker("ADBE")
print("Financials Columns:", ticker.financials.columns.tolist())
print("Fiscal Year End:", ticker.info.get('lastFiscalYearEnd'))
