
import sys
import os
import yfinance as yf
import pandas as pd
import datetime

# Add the directory to sys.path
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d')

def debug_q_counts(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    fy_end_month = 11 # For Adobe
    
    raw_data_map = {}
    
    def add_to_map(dt_obj, eps_val):
        adj_dt = dt_obj - datetime.timedelta(days=65)
        ey = adj_dt.year if adj_dt.month <= fy_end_month else adj_dt.year + 1
        yr_key = str(ey)
        if yr_key not in raw_data_map: raw_data_map[yr_key] = {}
        dt_key = dt_obj.strftime('%Y-%m-%d')
        raw_data_map[yr_key][dt_key] = eps_val

    # Test Source A
    print("--- Source A (Earnings Dates) ---")
    ed = stock.get_earnings_dates(limit=32)
    if ed is not None:
        c_opts = [c for c in ed.columns if any(x in c for x in ['Reported', 'Actual', 'EPS', 'Earnings'])]
        col_name = c_opts[0] if c_opts else 'Reported EPS'
        for idx, row in ed.iterrows():
            val = row.get(col_name)
            if val is not None and not pd.isna(val):
                add_to_map(pd.to_datetime(idx).tz_localize(None), val)

    # Test Source C
    print("--- Source C (Earnings History) ---")
    eh = stock.earnings_history
    if eh is not None:
        for idx, row in eh.iterrows():
            val = row.get('epsActual')
            if val is not None and not pd.isna(val):
                add_to_map(pd.to_datetime(idx).tz_localize(None), val)

    print("\n--- Summary ---")
    for yr in sorted(raw_data_map.keys()):
        qs = raw_data_map[yr]
        print(f"Year {yr}: {len(qs)} quarters - Values: {list(qs.values())}")

if __name__ == "__main__":
    debug_q_counts("ADBE")
