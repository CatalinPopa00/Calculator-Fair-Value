import yfinance as yf
import datetime
import pandas as _pd

stock = yf.Ticker('ADBE')
ed = stock.get_earnings_dates(limit=24)

fy_end_month = 11

adjusted_history = {}
if ed is not None and not ed.empty and 'Reported EPS' in ed.columns:
    for idx, row in ed.iterrows():
        val = row.get('Reported EPS')
        if val is not None and not _pd.isna(val) and isinstance(idx, (_pd.Timestamp, datetime.datetime)):
            # Subtract 45 days to approximate the quarter end date
            adjusted_date = idx - datetime.timedelta(days=45)
            ey = adjusted_date.year if adjusted_date.month <= fy_end_month else adjusted_date.year + 1
            if str(ey) not in adjusted_history:
                adjusted_history[str(ey)] = []
            adjusted_history[str(ey)].append(float(val))

final_adj_history = {}
for ey, quarters in adjusted_history.items():
    if len(quarters) >= 3:
        final_adj_history[ey] = sum(quarters) * (4.0 / len(quarters))
adjusted_history = final_adj_history

print("Adjusted History:", adjusted_history)

financials = stock.financials
is_cols = [c for c in financials.columns if str(c).upper() != "TTM"]
for yr_col in sorted(is_cols)[-4:]:
    year_label = str(yr_col.year) if hasattr(yr_col, 'year') else str(yr_col)[:4]
    
    print(f"Financials yr_col: {yr_col}, yr_col.year: {yr_col.year}, year_label: {year_label}")
    if year_label in adjusted_history:
        print(f"MATCHED! Will overwrite EPS with {adjusted_history[year_label]}")
    else:
        print(f"MISMATCH for {year_label}!")
