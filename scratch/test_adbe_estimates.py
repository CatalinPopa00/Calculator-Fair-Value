import yfinance as yf
import pandas as pd

def get_estimates(symbol):
    t = yf.Ticker(symbol)
    
    print("--- Earnings Dates (Surprise Data) ---")
    try:
        ed = t.earnings_dates
        if ed is not None:
            print(ed.head(10))
    except Exception as e:
        print("Error:", e)

    print("\n--- Earnings Estimate ---")
    try:
        ee = t.earnings_estimate
        if ee is not None:
            print(ee)
    except Exception as e:
        print("Error:", e)

    print("\n--- Revenue Estimate ---")
    try:
        re = t.revenue_estimate
        if re is not None:
            print(re)
    except Exception as e:
        print("Error:", e)
        
    print("\n--- EPS Trend ---")
    try:
        et = t.eps_trend
        if et is not None:
            print(et)
    except Exception as e:
        print("Error:", e)

get_estimates('ADBE')
