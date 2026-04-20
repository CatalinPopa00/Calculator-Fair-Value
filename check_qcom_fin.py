import sys
import os
import yfinance as yf
import pandas as pd

ticker = "QCOM"
stock = yf.Ticker(ticker)
fin = stock.financials
print(f"--- QCOM Financials (Annual) ---")
print(fin.to_string())

qfin = stock.quarterly_financials
print(f"\n--- QCOM Financials (Quarterly) ---")
print(qfin.to_string())
