import yfinance as yf
import pandas as pd
import datetime
import json
import requests

ticker_symbol = "HIMS"
stock = yf.Ticker(ticker_symbol)
info = stock.info

def get_nasdaq_earnings_surprise(ticker: str) -> list:
    try:
        url = f"https://api.nasdaq.com/api/company/{ticker.upper()}/earnings-surprise"
        headers = {
            'User-Agent': "Mozilla/5.0",
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://www.nasdaq.com',
            'Referer': 'https://www.nasdaq.com/'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            rows = data.get('data', {}).get('earningsSurpriseTable', {}).get('rows', [])
            return rows
    except: pass
    return []

adjusted_history = {}
raw_data_map = {} 
fy_end_month = 12

def add_to_map(dt_obj, eps_val):
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

print("Fetching earnings dates...")
ed = stock.get_earnings_dates(limit=32)
if ed is not None and not ed.empty:
    c_opts = [c for c in ed.columns if any(x in c for x in ['Reported', 'Actual', 'EPS', 'Earnings'])]
    col_name = c_opts[0] if c_opts else 'Reported EPS'
    if col_name in ed.columns:
        for idx, val in ed[col_name].items():
            if val is not None and not pd.isna(val):
                dt = pd.to_datetime(idx).tz_localize(None)
                add_to_map(dt, val)

print("Fetching Nasdaq surprises...")
nq_surprises = get_nasdaq_earnings_surprise(ticker_symbol)
for row in nq_surprises:
    eps_val = row.get('eps')
    dt_str = row.get('dateReported')
    if eps_val is not None and dt_str:
        dt = datetime.datetime.strptime(dt_str, '%m/%d/%Y')
        add_to_map(dt, float(eps_val))

print("Fetching earnings history...")
eh = stock.earnings_history
if eh is not None and not eh.empty:
    for idx, row in eh.iterrows():
        val = row.get('epsActual')
        if val is not None and not pd.isna(val):
            dt = pd.to_datetime(idx).tz_localize(None)
            add_to_map(dt, val)

now = datetime.datetime.now()
curr_y = now.year
for ey, quarters_dict in raw_data_map.items():
    vals = [v for v in quarters_dict.values() if v is not None]
    if not vals: continue
    total = sum(vals)
    count = len(vals)
    ey_int = int(ey)
    if count >= 4: adjusted_history[ey] = total
    elif count >= 1 and ey_int >= (curr_y - 1): adjusted_history[ey] = (total / count) * 4.0
    elif count >= 2: adjusted_history[ey] = (total / count) * 4.0
    else: adjusted_history[ey] = total

print(f"\nRaw Data Map: {json.dumps(raw_data_map, indent=2)}")
print(f"\nAdjusted History: {json.dumps(adjusted_history, indent=2)}")

print("\nFinancials:")
print(stock.financials.loc['Diluted EPS'] if 'Diluted EPS' in stock.financials.index else "No Diluted EPS")
