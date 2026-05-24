import os

filepath = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value\scraper\yahoo.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

beneish_snippet = '''        # Extract Beneish M-Score Data
        beneish_data = None
        try:
            if financials is not None and not financials.empty and bs is not None and not bs.empty and cashflow is not None and not cashflow.empty:
                # We need the two most recent annual columns
                cols = [c for c in bs.columns if str(c).upper() != "TTM"]
                if len(cols) >= 2:
                    col_curr = cols[0]
                    col_prev = cols[1]
                    
                    def get_val(df, fields, col):
                        for f in fields:
                            idx = find_idx(df, f)
                            if idx:
                                val = df.loc[idx, col]
                                if not pd.isna(val): return float(val)
                        return None
                    
                    beneish_data = {
                        "current": {
                            "net_receivables": get_val(bs, ['Net Receivables', 'Accounts Receivable'], col_curr),
                            "sales": get_val(financials, ['Total Revenue', 'Operating Revenue'], col_curr),
                            "gross_profit": get_val(financials, ['Gross Profit'], col_curr),
                            "current_assets": get_val(bs, ['Total Current Assets', 'Current Assets'], col_curr),
                            "ppe": get_val(bs, ['Net PPE', 'Gross PPE'], col_curr),
                            "total_assets": get_val(bs, ['Total Assets'], col_curr),
                            "depreciation": get_val(cashflow, ['Depreciation And Amortization', 'Depreciation'], col_curr) or get_val(financials, ['Reconciled Depreciation'], col_curr),
                            "sga": get_val(financials, ['Selling General And Administration', 'SG&A'], col_curr),
                            "current_liabilities": get_val(bs, ['Total Current Liabilities', 'Current Liabilities'], col_curr),
                            "long_term_debt": get_val(bs, ['Long Term Debt', 'Total Long Term Debt'], col_curr),
                            "cfo": get_val(cashflow, ['Operating Cash Flow', 'Total Cash From Operating Activities'], col_curr),
                            "net_income_cont": get_val(financials, ['Net Income From Continuing Ops', 'Net Income', 'Net Income Common Stockholders'], col_curr)
                        },
                        "prev": {
                            "net_receivables": get_val(bs, ['Net Receivables', 'Accounts Receivable'], col_prev),
                            "sales": get_val(financials, ['Total Revenue', 'Operating Revenue'], col_prev),
                            "gross_profit": get_val(financials, ['Gross Profit'], col_prev),
                            "current_assets": get_val(bs, ['Total Current Assets', 'Current Assets'], col_prev),
                            "ppe": get_val(bs, ['Net PPE', 'Gross PPE'], col_prev),
                            "total_assets": get_val(bs, ['Total Assets'], col_prev),
                            "depreciation": get_val(cashflow, ['Depreciation And Amortization', 'Depreciation'], col_prev) or get_val(financials, ['Reconciled Depreciation'], col_prev),
                            "sga": get_val(financials, ['Selling General And Administration', 'SG&A'], col_prev),
                            "current_liabilities": get_val(bs, ['Total Current Liabilities', 'Current Liabilities'], col_prev),
                            "long_term_debt": get_val(bs, ['Long Term Debt', 'Total Long Term Debt'], col_prev)
                        }
                    }
        except Exception as e_beneish:
            print(f"Error fetching Beneish Data: {e_beneish}")
'''

# We also need to add "beneish_data": beneish_data to the final return object
# We'll replace "# Final return object (Diagnostic-Rich v22)" with the snippet + the comment, and then find "company_overview_synthesis" to insert beneish_data

if "beneish_data" not in content:
    target = "# Final return object (Diagnostic-Rich v22)"
    content = content.replace(target, beneish_snippet + "\n        " + target)
    
    target_json = '"company_overview_synthesis": get_company_synthesis(ticker_symbol, info, run_ai=False)'
    content = content.replace(target_json, target_json + ',\n            "beneish_data": beneish_data')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated yahoo.py")
