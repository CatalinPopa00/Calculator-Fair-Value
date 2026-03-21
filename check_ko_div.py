import yfinance as yf
stock = yf.Ticker("KO")
divs = stock.dividends
if not divs.empty:
    div_annual = divs.groupby(divs.index.year).sum()
    print("Annual Dividends:")
    print(div_annual.tail(10))
else:
    print("No dividends found.")
