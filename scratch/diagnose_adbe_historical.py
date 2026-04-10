import yfinance as yf
import datetime
import pandas as pd
import sys
import os

# Add the directory to sys.path
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d')

from scraper.yahoo import get_nasdaq_historical_eps

def diagnose_adbe():
    ticker_symbol = "ADBE"
    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    fy_end_month = 11 # Adobe
    
    raw_data_map = {}
    
    def add_to_map(dt_obj, eps_val):
        adj_dt = dt_obj - datetime.timedelta(days=65)
        ey = adj_dt.year if adj_dt.month <= fy_end_month else adj_dt.year + 1
        yr_key = str(ey)
        if yr_key not in raw_data_map: raw_data_map[yr_key] = {}
        dt_key = dt_obj.strftime('%Y-%m-%d')
        raw_data_map[yr_key][dt_key] = float(eps_val)

    # 1. YF Earnings Dates
    try:
        ed = stock.get_earnings_dates(limit=32)
        if ed is not None and not ed.empty:
            for idx, row in ed.iterrows():
                val = row.get('Reported EPS') or row.get('Actual EPS')
                if val is not None and not pd.isna(val):
                    add_to_map(pd.to_datetime(idx).tz_localize(None), val)
    except: pass

    # 2. Nasdaq
    try:
        nq_hist = get_nasdaq_historical_eps(ticker_symbol)
        for entry in nq_hist:
            add_to_map(entry['date'], entry['eps'])
    except: pass

    # 3. EH
    try:
        eh = stock.earnings_history
        if eh is not None and not eh.empty:
            for idx, row in eh.iterrows():
                val = row.get('epsActual')
                if val is not None and not pd.isna(val):
                    add_to_map(pd.to_datetime(idx).tz_localize(None), val)
    except: pass

    print("--- RAW DATA MAP ---")
    for yr, data in sorted(raw_data_map.items()):
        vals = list(data.values())
        print(f"FY {yr}: Count={len(vals)}, Sum={sum(vals):.2f}, Values={data}")

if __name__ == "__main__":
    diagnose_adbe()
