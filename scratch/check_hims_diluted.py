
import yfinance as yf
ticker = yf.Ticker("HIMS")
financials = ticker.financials
if "Diluted Average Shares" in financials.index:
    print("Diluted Shares 2025:")
    print(financials.loc["Diluted Average Shares"])
else:
    print("No Diluted Average Shares row found.")
