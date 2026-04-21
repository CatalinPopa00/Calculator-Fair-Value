
import yfinance as yf
ticker = "AAPL"
stock = yf.Ticker(ticker)

print("Earnings History (Last 4):")
eh = stock.earnings_history
if eh is not None and not eh.empty:
    print(eh.sort_index(ascending=False).head(4)[['epsActual', 'epsEstimate']])

print("\nIncome Statement (Diluted EPS):")
fin = stock.financials
try:
    print(fin.loc['Diluted EPS'])
except:
    print("Diluted EPS not found")

print("\nIncome Statement (Diluted Average Shares):")
try:
    print(fin.loc['Diluted Average Shares'])
except:
    print("Diluted Average Shares not found")

print("\nCash Flow (Stock Based Compensation):")
cf = stock.cashflow
try:
    print(cf.loc['Stock Based Compensation'])
except:
    print("Stock Based Compensation not found")
