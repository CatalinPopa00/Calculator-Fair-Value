
import yfinance as yf
import pandas as pd

ticker = yf.Ticker("HIMS")
financials = ticker.financials
print("HIMS Financials (Net Income):")
print(financials.loc["Net Income"])

cf = ticker.cashflow
print("\nHIMS Cashflow (SBC):")
print(cf.loc["Stock Based Compensation"])

print("\nHIMS Financials (Shares):")
print(financials.loc["Basic Average Shares"])
