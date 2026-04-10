
import yfinance as yf
import pandas as pd
import datetime

def test_ticker(ticker):
    stock = yf.Ticker(ticker)
    print(f"\n--- {ticker} ---")
    
    # 1. Earnings Estimate (Projections)
    print("\nEarnings Estimate (Projections):")
    try:
        ee = stock.earnings_estimate
        if ee is not None:
            print(ee)
        else:
            print("No earnings_estimate found.")
    except Exception as e:
        print(f"Error fetching earnings_estimate: {e}")

    # 2. Earnings Dates (Historical Non-GAAP)
    print("\nEarnings Dates (Historical Non-GAAP):")
    try:
        ed = stock.get_earnings_dates(limit=24)
        if ed is not None:
            # Filter for rows with Reported EPS
            reported = ed[ed['Reported EPS'].notna()]
            print(reported[['Reported EPS']])
        else:
            print("No earnings_dates found.")
    except Exception as e:
        print(f"Error fetching earnings_dates: {e}")

    # 3. Financials (GAAP)
    print("\nFinancials (GAAP Diluted EPS):")
    try:
        fin = stock.financials
        if fin is not None and 'Diluted EPS' in fin.index:
            print(fin.loc['Diluted EPS'])
        else:
            print("No Diluted EPS in financials.")
    except Exception as e:
        print(f"Error fetching financials: {e}")

if __name__ == "__main__":
    test_ticker("ADBE")
    test_ticker("META")
