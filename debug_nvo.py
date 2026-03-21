import yfinance as yf
s = yf.Ticker('NVO')
i = s.info
print(f"FCF: {i.get('freeCashflow')}")
print(f"OCF: {i.get('operatingCashflow')}")
print(f"Rev: {i.get('totalRevenue')}")
print(f"Cur: {i.get('currency')}")
print(f"FinCur: {i.get('financialCurrency')}")
