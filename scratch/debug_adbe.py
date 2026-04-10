
import yfinance as yf
import pandas as pd
import datetime

def debug_adbe():
    t = "ADBE"
    stock = yf.Ticker(t)
    
    # 1. Check earnings dates columns and content
    ed = stock.get_earnings_dates(limit=40)
    print("--- Earnings Dates Cols ---")
    print(ed.columns.tolist())
    print("--- Earnings Dates Head (10) ---")
    print(ed.head(10))
    
    # 2. Check earnings history
    eh = stock.earnings_history
    print("--- Earnings History Head ---")
    print(eh.head(10))
    
    # 3. Check info
    info = stock.info
    print(f"lastFiscalYearEnd: {info.get('lastFiscalYearEnd')}")
    lfy_dt = datetime.datetime.fromtimestamp(info.get('lastFiscalYearEnd'))
    print(f"Parsed LFY Date: {lfy_dt}")

if __name__ == "__main__":
    debug_adbe()
