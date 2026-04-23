import yfinance as yf
import pandas as pd

def test_yfinance_estimates(ticker):
    stock = yf.Ticker(ticker)
    print(f"--- Estimates for {ticker} ---")
    
    # yfinance often exposes these
    try:
        ee = stock.earnings_estimate
        if ee is not None:
            print("\nEarnings Estimate:")
            print(ee)
    except Exception as e:
        print(f"Error fetching earnings_estimate: {e}")

    try:
        re = stock.revenue_estimate
        if re is not None:
            print("\nRevenue Estimate:")
            print(re)
    except Exception as e:
        print(f"Error fetching revenue_estimate: {e}")

if __name__ == "__main__":
    test_yfinance_estimates("META")
