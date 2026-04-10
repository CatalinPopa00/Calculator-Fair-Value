
import yfinance as yf
import pandas as pd

def test_adbe():
    stock = yf.Ticker("ADBE")
    print("--- ADBE Earnings Dates ---")
    ed = stock.get_earnings_dates(limit=32)
    if ed is not None:
        print(ed[['Reported EPS']])
    else:
        print("No earnings dates")

if __name__ == "__main__":
    test_adbe()
