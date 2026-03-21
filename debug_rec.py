import yfinance as yf
import json
import pandas as pd

def debug_rec(ticker):
    print(f"\n--- {ticker} ---")
    try:
        s = yf.Ticker(ticker)
        info = s.info
        print(f"recommendationMean: {info.get('recommendationMean')}")
        print(f"recommendationKey: {info.get('recommendationKey')}")
        
        rs = s.recommendations_summary
        if rs is not None and not rs.empty:
            print("Recommendation Summary (Latest):")
            print(rs.iloc[0].to_dict())
        else:
            print("No recommendation summary (empty)")
    except Exception as e:
        print(f"Error for {ticker}: {e}")

if __name__ == "__main__":
    for t in ["AAPL", "NVO", "MSFT", "META", "TSM"]:
        debug_rec(t)
