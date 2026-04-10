
import yfinance as yf
import json
import pandas as pd

def explore_yf_history(ticker):
    stock = yf.Ticker(ticker)
    print(f"--- Exploring {ticker} ---")
    
    # Check earnings history (Normalized vs GAAP)
    try:
        hist = stock.earnings_history
        if hist is not None:
            print("Earnings History (Normalized):")
            print(hist)
    except Exception as e:
        print(f"stock.earnings_history failed: {e}")

    # Check info for any related keys
    info = stock.info
    print("\nInteresting Info Keys:")
    for k in info.keys():
        if 'eps' in k.lower() or 'earnings' in k.lower():
            print(f"{k}: {info[k]}")

    # Check financials for 'Normalized' rows
    try:
        financials = stock.financials
        print("\nFinancials Rows:")
        print(financials.index.tolist())
        if 'Normalized Income' in financials.index:
            print("\nNormalized Income:")
            print(financials.loc['Normalized Income'])
    except Exception as e:
        print(f"stock.financials failed: {e}")

if __name__ == "__main__":
    explore_yf_history("ADBE")
    explore_yf_history("META")
