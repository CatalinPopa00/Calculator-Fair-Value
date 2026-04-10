
import yfinance as yf
import pandas as pd

def check_meta_projections():
    stock = yf.Ticker("META")
    
    # Check earnings estimates
    print("--- Earnings Estimates (Next Years) ---")
    try:
        ee = stock.earnings_estimates
        print(ee)
    except Exception as e:
        print(f"Failed to get earnings_estimates: {e}")

    # Check the 'Analysis' tab data in yfinance
    try:
        # yfinance stores this in a internal dict
        print("\n--- Analyst Estimates (Manual Fetch) ---")
        analyst_data = stock.get_earnings_estimates()
        print(analyst_data)
    except: pass

if __name__ == "__main__":
    check_meta_projections()
