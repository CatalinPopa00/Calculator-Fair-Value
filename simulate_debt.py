import yfinance as yf
import pandas as pd

def find_idx(df, target):
    if df is None or df.empty: return None
    target_lower = str(target).lower().strip()
    for idx in df.index:
        if str(idx).lower().strip() == target_lower: return idx
    return None

def get_strict_debt(df):
    if df is None or df.empty: return 0
    lt_idx = find_idx(df, 'Long Term Debt') or find_idx(df, 'Total Long Term Debt')
    st_idx = find_idx(df, 'Current Debt') or find_idx(df, 'Short Term Debt') or find_idx(df, 'Short Long Term Debt') or find_idx(df, 'Commercial Paper')
    
    lt = float(df.loc[lt_idx].iloc[0]) if lt_idx else 0
    st = float(df.loc[st_idx].iloc[0]) if st_idx else 0
    return (lt + st)

ticker = yf.Ticker('GOOGL')
q_bs = ticker.quarterly_balance_sheet
bs = ticker.balance_sheet
info = ticker.info

td_raw = get_strict_debt(q_bs) or get_strict_debt(bs)
total_debt = td_raw if td_raw > 0 else info.get('totalDebt', 0)

print(f"LT IDX in Q_BS: {find_idx(q_bs, 'Long Term Debt')}")
print(f"ST IDX in Q_BS: {find_idx(q_bs, 'Current Debt')}")
print(f"TD_RAW: {td_raw}")
print(f"INFO TOTAL DEBT: {info.get('totalDebt')}")
print(f"FINAL TOTAL DEBT: {total_debt}")
