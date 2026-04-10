
import yfinance as yf
import pandas as pd
import datetime

def solve_adbe():
    ticker = "ADBE"
    stock = yf.Ticker(ticker)
    info = stock.info
    lfy_ts = info.get('lastFiscalYearEnd')
    lfy_dt = datetime.datetime.fromtimestamp(lfy_ts)
    fy_end_month = lfy_dt.month
    print(f"FY End Month: {fy_end_month}")
    
    # 1. Check earnings dates
    ed = stock.get_earnings_dates(limit=40)
    print("--- Earnings Dates (First 10) ---")
    print(ed.head(10))
    
    # 2. Check earnings history
    eh = stock.earnings_history
    print("--- Earnings History (First 10) ---")
    print(eh.head(10))
    
    # 3. Check estimates
    ee = stock.earnings_estimate
    print("--- Earnings Estimates ---")
    print(ee)

if __name__ == "__main__":
    solve_adbe()
