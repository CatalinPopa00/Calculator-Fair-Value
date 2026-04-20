
import yfinance as yf
ticker = yf.Ticker("HIMS")
qcf = ticker.quarterly_cashflow
if "Stock Based Compensation" in qcf.index:
    print("Quarterly SBC:")
    print(qcf.loc["Stock Based Compensation"])
else:
    print("No Quarterly SBC row found.")
