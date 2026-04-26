import yfinance as yf
import pandas as pd

ticker = "META"
stock = yf.Ticker(ticker)
rt = getattr(stock, 'recommendations', None)

if rt is not None:
    print("Recommendations Index:")
    print(rt.index)
    print("\nRecommendations Columns:")
    print(rt.columns)
    print("\nFirst row:")
    print(rt.iloc[0])
    print("\nLast row:")
    print(rt.iloc[-1])
else:
    print("No recommendations found via yfinance.")
