import yfinance as yf
import pandas as pd
from datetime import datetime

stock = yf.Ticker('SMCI')
info = stock.info

# Check fiscal year info
lfy_ts = info.get('lastFiscalYearEnd')
mrq_ts = info.get('mostRecentQuarter')
lfy_dt = datetime.fromtimestamp(lfy_ts) if lfy_ts else None
mrq_dt = datetime.fromtimestamp(mrq_ts) if mrq_ts else None
print(f"Last FY End: {lfy_dt}")
print(f"MRQ: {mrq_dt}")

# Check quarterly revenue
istmt = stock.quarterly_income_stmt
if 'Total Revenue' in istmt.index:
    rev_row = istmt.loc['Total Revenue']
    for c in list(rev_row.index)[:10]:
        val = rev_row[c]
        if not pd.isna(val):
            # Compute fiscal quarter label
            fy_end_month = lfy_dt.month if lfy_dt else 12
            fy_start_month = (fy_end_month % 12) + 1
            months_off = (c.month - fy_start_month) % 12
            fq = (months_off // 3) + 1
            if c.month <= fy_end_month:
                fy = c.year
            else:
                fy = c.year + 1
            label = f"Q{fq} {fy}"
            print(f"  {c.date()} -> {label}: {val:,.0f}")
