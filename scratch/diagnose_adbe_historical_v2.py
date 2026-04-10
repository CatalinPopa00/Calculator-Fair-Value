import yfinance as yf
import datetime
import pandas as pd
import sys
import os

# Add the directory to sys.path
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d')

from scraper.yahoo import get_nasdaq_historical_eps

def diagnose_actual_logic():
    ticker_symbol = "ADBE"
    stock = yf.Ticker(ticker_symbol)
    fy_end_month = 11
    
    adjusted_history = {}
    raw_data_map = {}
    
    def add_to_map(dt_obj, eps_val):
        try:
            adj_dt = dt_obj - datetime.timedelta(days=65)
            ey = adj_dt.year if adj_dt.month <= fy_end_month else adj_dt.year + 1
            yr_key = str(ey)
            if yr_key not in raw_data_map: raw_data_map[yr_key] = {}
            
            found_duplicate = False
            for existing_dt_str in raw_data_map[yr_key].keys():
                existing_dt = datetime.datetime.strptime(existing_dt_str, '%Y-%m-%d')
                if abs((dt_obj - existing_dt).days) <= 45:
                    if abs(eps_val) > abs(raw_data_map[yr_key][existing_dt_str]):
                        raw_data_map[yr_key][existing_dt_str] = float(eps_val)
                    found_duplicate = True
                    break
            
            if not found_duplicate:
                dt_key = dt_obj.strftime('%Y-%m-%d')
                raw_data_map[yr_key][dt_key] = float(eps_val)
        except: pass

    # Sources
    try:
        ed = stock.get_earnings_dates(limit=60)
        if ed is not None and not ed.empty:
            for idx, row in ed.iterrows():
                val = row.get('Reported EPS') or row.get('Actual EPS')
                if val is not None and not pd.isna(val):
                    add_to_map(pd.to_datetime(idx).tz_localize(None), val)
    except: pass

    try:
        nq_hist = get_nasdaq_historical_eps(ticker_symbol)
        for entry in nq_hist:
            add_to_map(entry['date'], entry['eps'])
    except: pass

    try:
        eh = stock.earnings_history
        if eh is not None and not eh.empty:
            for idx, row in eh.iterrows():
                val = row.get('epsActual')
                if val is not None and not pd.isna(val):
                    add_to_map(pd.to_datetime(idx).tz_localize(None), val)
    except: pass

    # Consolidate
    now = datetime.datetime.now()
    curr_y = now.year
    for ey, quarters_dict in raw_data_map.items():
        vals = list(quarters_dict.values())
        count = len(vals)
        total = sum(vals)
        ey_int = int(ey)
        
        if count >= 4:
            adjusted_history[ey] = total
        elif count >= 1 and ey_int >= (curr_y - 1):
            adjusted_history[ey] = (total / count) * 4.0
        else:
            adjusted_history[ey] = (total / count) * 4.0 if count >= 2 else 0

    print("--- CONSOLIDATED HISTORY ---")
    for yr, val in sorted(adjusted_history.items()):
        print(f"FY {yr}: {val:.2f} (from {len(raw_data_map[yr])} qtrs)")

if __name__ == "__main__":
    diagnose_actual_logic()
