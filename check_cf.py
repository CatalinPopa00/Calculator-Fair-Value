import yfinance as yf
s = yf.Ticker('NVO')
cf = s.cashflow
print("Cashflow index:")
print(cf.index.tolist())
if 'Free Cash Flow' in cf.index:
    print("\nFree Cash Flow (latest):")
    print(cf.loc['Free Cash Flow'].iloc[0])
if 'Operating Cash Flow' in cf.index:
    print("\nOperating Cash Flow (latest):")
    print(cf.loc['Operating Cash Flow'].iloc[0])
