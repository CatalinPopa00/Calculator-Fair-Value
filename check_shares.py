import yfinance as yf
ticker = 'NVO'
stock = yf.Ticker(ticker)
info = stock.info
print(f"Shares Outstanding (info): {info.get('sharesOutstanding')}")
financials = stock.financials
for k in ['Diluted Average Shares', 'Basic Average Shares']:
    if k in financials.index:
        print(f"{k} (raw): {financials.loc[k].iloc[0]}")
