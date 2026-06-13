import yfinance as yf
from models.scoring import calculate_beneish_m_score
import pandas as pd
ticker = yf.Ticker("NVDA")
bs = ticker.balance_sheet
fin = ticker.financials
cf = ticker.cashflow
cols = [c for c in bs.columns if str(c).upper() != "TTM"]

if len(cols) >= 2:
    col_curr = cols[0]
    col_prev = cols[1]

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

    curr = {
        "net_receivables": get_val(bs, ['Net Receivables', 'Accounts Receivable'], col_curr),
        "sales": get_val(fin, ['Total Revenue', 'Operating Revenue'], col_curr),
        "gross_profit": get_val(fin, ['Gross Profit'], col_curr),
        "current_assets": get_val(bs, ['Total Current Assets', 'Current Assets'], col_curr),
        "ppe": get_val(bs, ['Net PPE', 'Gross PPE'], col_curr),
        "total_assets": get_val(bs, ['Total Assets'], col_curr),
        "depreciation": get_val(cf, ['Depreciation And Amortization', 'Depreciation'], col_curr) or get_val(fin, ['Reconciled Depreciation'], col_curr),
        "sga": get_val(fin, ['Selling General And Administration', 'SG&A'], col_curr),
        "current_liabilities": get_val(bs, ['Total Current Liabilities', 'Current Liabilities'], col_curr),
        "long_term_debt": get_val(bs, ['Long Term Debt', 'Total Long Term Debt'], col_curr),
        "cfo": get_val(cf, ['Operating Cash Flow', 'Total Cash From Operating Activities'], col_curr),
        "net_income_cont": get_val(fin, ['Net Income From Continuing Ops', 'Net Income', 'Net Income Common Stockholders'], col_curr)
    }
    prev = {
        "net_receivables": get_val(bs, ['Net Receivables', 'Accounts Receivable'], col_prev),
        "sales": get_val(fin, ['Total Revenue', 'Operating Revenue'], col_prev),
        "gross_profit": get_val(fin, ['Gross Profit'], col_prev),
        "current_assets": get_val(bs, ['Total Current Assets', 'Current Assets'], col_prev),
        "ppe": get_val(bs, ['Net PPE', 'Gross PPE'], col_prev),
        "total_assets": get_val(bs, ['Total Assets'], col_prev),
        "depreciation": get_val(cf, ['Depreciation And Amortization', 'Depreciation'], col_prev) or get_val(fin, ['Reconciled Depreciation'], col_prev),
        "sga": get_val(fin, ['Selling General And Administration', 'SG&A'], col_prev),
        "current_liabilities": get_val(bs, ['Total Current Liabilities', 'Current Liabilities'], col_prev),
        "long_term_debt": get_val(bs, ['Long Term Debt', 'Total Long Term Debt'], col_prev)
    }
    beneish_data = {'current': curr, 'prev': prev}
    res = calculate_beneish_m_score({'beneish_data': beneish_data})
    import json
    print(json.dumps(res, indent=2))
