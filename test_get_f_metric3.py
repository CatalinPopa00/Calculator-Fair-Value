import time
import pandas as pd
import numpy as np

def find_nearest_col(df, target_date, max_days=10):
    try:
        if isinstance(target_date, str):
            target_dt = pd.to_datetime(target_date).date()
        elif hasattr(target_date, 'date'):
            target_dt = target_date.date()
        else:
            target_dt = pd.to_datetime(target_date).date()
    except:
        return None
    best_col = None
    min_delta = 9999
    for col in df.columns:
        try:
            if hasattr(col, 'date'):
                col_dt = col.date()
            else:
                col_dt = pd.to_datetime(col).date()
            delta = abs((col_dt - target_dt).days)
            if delta < min_delta and delta <= max_days:
                min_delta = delta
                best_col = col
        except: continue
    return best_col

def find_idx(df, target):
    if df is None or (hasattr(df, "empty") and df.empty) or (isinstance(df, dict) and not df): return None
    targets = [str(t).lower().strip() for t in (target if isinstance(target, list) else [target])]
    for idx in df.index:
        idx_lower = str(idx).lower().strip()
        if idx_lower in targets: return idx
    return None

financials = pd.DataFrame(np.random.rand(100, 10), columns=pd.date_range("2020-01-01", periods=10, freq="YE"))
financials.index = [f"Metric {i}" for i in range(100)]
financials.loc["Total Revenue"] = 100
financials.loc["Net Income Common Stock Holders"] = 20
financials.loc["Operating Income"] = 30

bs = pd.DataFrame(np.random.rand(100, 10), columns=pd.date_range("2020-01-01", periods=10, freq="YE"))
bs.index = [f"BS Metric {i}" for i in range(100)]
bs.loc["Current Assets"] = 50
bs.loc["Current Liabilities"] = 40
bs.loc["Common Stock Equity"] = 60
bs.loc["Total Assets"] = 100
bs.loc["Total Debt"] = 20

_pd = pd

target_date = financials.columns[-1]

# baseline
def get_f_metric_old(df, keys, date):
    for k in keys:
        idx = find_idx(df, k)
        if idx:
            c_idx = find_nearest_col(df, date)
            if c_idx:
                val = df.loc[idx, c_idx]
                if not _pd.isna(val): return float(val)
    return 0

start = time.time()
for _ in range(1000):
    rev_val = get_f_metric_old(financials, ['Total Revenue', 'Revenue'], target_date)
    ni_val = get_f_metric_old(financials, ['Net Income Common Stock Holders', 'Net Income'], target_date)
    op_inc_val = get_f_metric_old(financials, ['Operating Income', 'EBIT'], target_date)
    ca = get_f_metric_old(bs, ['Current Assets', 'Total Current Assets'], target_date)
    cl = get_f_metric_old(bs, ['Current Liabilities', 'Total Current Liabilities'], target_date)
    equity = get_f_metric_old(bs, ['Common Stock Equity', 'Stockholders Equity', 'Total Equity'], target_date)
    assets_val = get_f_metric_old(bs, ['Total Assets'], target_date)
    debt_val = get_f_metric_old(bs, ['Total Debt'], target_date)
end = time.time()
print(f"Old approach took: {end - start:.4f}s")


_col_cache = {}
_idx_cache = {}
def get_f_metric_new(df, keys, date):
    df_id = id(df)
    col_key = (df_id, date)
    if col_key not in _col_cache:
        _col_cache[col_key] = find_nearest_col(df, date)
    c_idx = _col_cache[col_key]

    if c_idx:
        for k in keys:
            idx_key = (df_id, k)
            if idx_key not in _idx_cache:
                _idx_cache[idx_key] = find_idx(df, k)
            idx = _idx_cache[idx_key]
            if idx:
                val = df.loc[idx, c_idx]
                if not _pd.isna(val): return float(val)
    return 0

start = time.time()
for _ in range(1000):
    rev_val = get_f_metric_new(financials, ['Total Revenue', 'Revenue'], target_date)
    ni_val = get_f_metric_new(financials, ['Net Income Common Stock Holders', 'Net Income'], target_date)
    op_inc_val = get_f_metric_new(financials, ['Operating Income', 'EBIT'], target_date)
    ca = get_f_metric_new(bs, ['Current Assets', 'Total Current Assets'], target_date)
    cl = get_f_metric_new(bs, ['Current Liabilities', 'Total Current Liabilities'], target_date)
    equity = get_f_metric_new(bs, ['Common Stock Equity', 'Stockholders Equity', 'Total Equity'], target_date)
    assets_val = get_f_metric_new(bs, ['Total Assets'], target_date)
    debt_val = get_f_metric_new(bs, ['Total Debt'], target_date)
end = time.time()
print(f"New approach took: {end - start:.4f}s")
