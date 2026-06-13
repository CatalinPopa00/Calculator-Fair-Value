import yfinance as yf
from models.scoring import calculate_beneish_m_score
import pandas as pd
ticker = yf.Ticker("NVDA")
bs = ticker.balance_sheet
fin = ticker.financials
cf = ticker.cashflow
cols = [c for c in bs.columns if str(c).upper() != "TTM"]

col_curr = cols[0]

def find_idx(df, field):
    for idx in df.index:
        if field.lower() == str(idx).lower():
            return idx
    for idx in df.index:
        if field.lower() in str(idx).lower():
            return idx
    return None

def get_val(df, fields, col, default=None):
    for f in fields:
        idx = find_idx(df, f)
        if idx:
            val = df.loc[idx, col]
            if not pd.isna(val): return float(val)
    return default

net_income_cont = get_val(fin, ['Net Income From Continuing Ops', 'Net Income', 'Net Income Common Stockholders'], col_curr)
cfo = get_val(cf, ['Operating Cash Flow', 'Total Cash From Operating Activities'], col_curr)
total_assets = get_val(bs, ['Total Assets'], col_curr)

print(f"Net Income Cont: {net_income_cont}")
print(f"CFO: {cfo}")
print(f"Total Assets: {total_assets}")
print(f"TATA: {(net_income_cont - cfo) / total_assets}")
