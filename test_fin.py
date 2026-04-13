import yfinance as yf
ticker = yf.Ticker('SYF')
fin = ticker.financials
print(fin.index.tolist())
