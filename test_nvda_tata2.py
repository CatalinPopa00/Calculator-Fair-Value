import yfinance as yf
ticker = yf.Ticker("NVDA")
fin = ticker.financials
cf = ticker.cashflow
print(fin.loc[['Net Income From Continuing Operation Net Minority Interest', 'Net Income', 'Net Income Common Stockholders']])
print(cf.loc[['Operating Cash Flow']])
