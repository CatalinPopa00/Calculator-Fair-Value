import sys
import re
import os

# 1. Patch yahoo.py
try:
    with open('scraper/yahoo.py', 'r', encoding='utf-8') as f:
        yahoo = f.read()

    inject_code = """
            # --- PHASE 3: QUARTERLY ANCHORS ---
            quarterly_anchors = []
            try:
                if historical_anchors:
                    ttm_anchor = historical_anchors[0].copy()
                    ttm_anchor["year"] = "TTM"
                    quarterly_anchors.append(ttm_anchor)
                    
                if q_financials is not None and not (hasattr(q_financials, 'empty') and q_financials.empty):
                    # Extract up to 4 quarters
                    cols = q_financials.columns[:4]
                    for q_col in cols:
                        try:
                            # Safely get year and quarter
                            year_val = str(getattr(q_col, 'year', ''))[-2:]
                            q_val = getattr(q_col, 'quarter', '')
                            yr_label = f"Q{q_val} '{year_val}"
                            
                            def get_q_is_metric(field, col):
                                idx = find_idx(q_financials, field)
                                if not idx: return None
                                val = q_financials.loc[idx, col]
                                import pandas as pd
                                return float(val) if not pd.isna(val) else None
                                
                            def get_q_bs_metric(field, col):
                                if q_bs is None or (hasattr(q_bs, 'empty') and q_bs.empty) or (isinstance(q_bs, dict) and not q_bs): return None
                                idx = find_idx(q_bs, field)
                                if not idx: return None
                                val = q_bs.loc[idx, col]
                                import pandas as pd
                                return float(val) if not pd.isna(val) else None
                                
                            def get_q_cf_metric(field, col):
                                if q_cashflow is None or (hasattr(q_cashflow, 'empty') and q_cashflow.empty) or (isinstance(q_cashflow, dict) and not q_cashflow): return None
                                idx = find_idx(q_cashflow, field)
                                if not idx: return None
                                val = q_cashflow.loc[idx, col]
                                import pandas as pd
                                return float(val) if not pd.isna(val) else None

                            r_raw = get_q_is_metric('Total Revenue', q_col) or 0
                            e_raw = get_q_is_metric('Diluted EPS', q_col) or get_q_is_metric('Basic EPS', q_col) or 0
                            f_raw = get_q_cf_metric('Free Cash Flow', q_col) or 0
                            c_raw = get_q_bs_metric('Cash Cash Equivalents And Short Term Investments', q_col) or get_q_bs_metric('Cash And Cash Equivalents', q_col) or 0
                            
                            d_raw = get_q_bs_metric('Total Debt', q_col)
                            if d_raw is None:
                                lt_debt = get_q_bs_metric('Long Term Debt', q_col) or get_q_bs_metric('Total Long Term Debt', q_col) or 0
                                st_debt = get_q_bs_metric('Current Debt', q_col) or get_q_bs_metric('Short Term Debt', q_col) or 0
                                d_raw = lt_debt + st_debt

                            assets = get_q_bs_metric('Total Assets', q_col)
                            liabs = get_q_bs_metric('Current Liabilities', q_col) or get_q_bs_metric('Total Current Liabilities', q_col)
                            
                            s_raw = get_q_is_metric('Diluted Average Shares', q_col) or get_q_is_metric('Basic Average Shares', q_col) or 0
                            ni_raw = get_q_is_metric('Net Income', q_col) or 0

                            margin_v = (ni_raw / r_raw * 100.0) if (r_raw and r_raw > 0) else None
                            fcf_margin_v = (f_raw / r_raw * 100.0) if (r_raw and r_raw > 0) else None
                            
                            cr_v = None
                            ca_hist = get_q_bs_metric('Total Current Assets', q_col) or get_q_bs_metric('Current Assets', q_col)
                            cl_hist = get_q_bs_metric('Total Current Liabilities', q_col) or get_q_bs_metric('Current Liabilities', q_col)
                            if ca_hist and cl_hist and cl_hist > 0:
                                cr_v = ca_hist / cl_hist
                                
                            roic_v = (ni_raw / (assets - liabs) * 100.0) if (assets and liabs and (assets - liabs) > 0) else None

                            quarterly_anchors.append({
                                "year": yr_label,
                                "revenue_b": round(r_raw / 1e9, 2),
                                "eps": round(e_raw, 2),
                                "eps_adj": round(e_raw, 2),
                                "fcf_b": round(f_raw / 1e9, 2) if f_raw is not None else None,
                                "fcf_margin_pct": f"{fcf_margin_v:.1f}%" if fcf_margin_v is not None else "N/A",
                                "net_income_b": round(ni_raw / 1e9, 2),
                                "net_margin_pct": f"{margin_v:.1f}%" if margin_v is not None else "N/A",
                                "gaap_net_margin_pct": f"{margin_v:.1f}%" if margin_v is not None else "N/A",
                                "cash_b": round(c_raw / 1e9, 2),
                                "total_debt_b": round(d_raw / 1e9, 2),
                                "current_ratio": round(cr_v, 2) if cr_v is not None else None,
                                "shares_out_b": round(s_raw / 1e9, 3) if s_raw else None,
                                "roic_pct": f"{roic_v:.1f}%" if roic_v is not None else "N/A"
                            })
                        except Exception as q_e:
                            print("Error extracting q_anchor:", q_e)
            except Exception as e_q:
                print("Quarterly extraction error:", e_q)
"""
    
    if "quarterly_anchors =" not in yahoo:
        # Find where to inject: after `historical_anchors.reverse()` and before `# Final return object`
        target = '        # Final return object'
        yahoo = yahoo.replace(target, inject_code + '\n' + target)
        
        # Add to the return dict
        ret_target = '"historical_anchors": historical_anchors,'
        yahoo = yahoo.replace(ret_target, ret_target + '\n            "quarterly_anchors": quarterly_anchors,')
        
        with open('scraper/yahoo.py', 'w', encoding='utf-8') as f:
            f.write(yahoo)
        print("yahoo.py patched")
    else:
        print("yahoo.py already patched")

except Exception as e:
    print("Error patching yahoo.py:", e)

# 2. Patch api/index.py
try:
    with open('api/index.py', 'r', encoding='utf-8') as f:
        api = f.read()

    if "quarterly_anchors: Optional[list]" not in api:
        api = api.replace('historical_anchors: Optional[list] = None', 
                          'historical_anchors: Optional[list] = None\n    quarterly_anchors: Optional[list] = None')
        
        # Add to return dictionary at the end
        if '"quarterly_anchors": quarterly_anchors' not in api:
            api = re.sub(
                r'("historical_anchors": historical_anchors,)',
                r'\1\n            "quarterly_anchors": data.get("quarterly_anchors") or [],',
                api
            )
            
        with open('api/index.py', 'w', encoding='utf-8') as f:
            f.write(api)
        print("api/index.py patched")
    else:
        print("api/index.py already patched")
except Exception as e:
    print("Error patching api/index.py:", e)
