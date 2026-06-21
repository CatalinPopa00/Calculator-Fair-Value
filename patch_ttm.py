try:
    with open('scraper/yahoo.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    start_idx = -1
    end_idx = -1
    for i, line in enumerate(lines):
        if '# --- PHASE 3: QUARTERLY ANCHORS ---' in line:
            start_idx = i
        if '# Final return object' in line:
            end_idx = i

    if start_idx != -1 and end_idx != -1:
        new_q_anchors = """        # --- PHASE 3: QUARTERLY ANCHORS ---
        quarterly_anchors = []
        try:
            temp_q_anchors = []
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
                        
                        # Fetch Normalized EPS for Adjusted EPS
                        e_adj_raw = get_q_is_metric('Normalized EPS', q_col)
                        if e_adj_raw is None:
                            e_adj_raw = e_raw

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

                        temp_q_anchors.append({
                            "year": yr_label,
                            "revenue_b": round(r_raw / 1e9, 2),
                            "eps": round(e_raw, 2),
                            "eps_adj": round(e_adj_raw, 2),
                            "fcf_b": round(f_raw / 1e9, 2) if f_raw is not None else None,
                            "fcf_margin_pct": f"{fcf_margin_v:.1f}%" if fcf_margin_v is not None else "N/A",
                            "net_income_b": round(ni_raw / 1e9, 2),
                            "net_margin_pct": f"{margin_v:.1f}%" if margin_v is not None else "N/A",
                            "gaap_net_margin_pct": f"{margin_v:.1f}%" if margin_v is not None else "N/A",
                            "cash_b": round(c_raw / 1e9, 2),
                            "total_debt_b": round(d_raw / 1e9, 2),
                            "current_ratio": round(cr_v, 2) if cr_v is not None else None,
                            "shares_out_b": round(s_raw / 1e9, 3) if s_raw else None,
                            "roic_pct": f"{roic_v:.1f}%" if roic_v is not None else "N/A",
                            "_raw": { 
                                "r": r_raw, "e": e_raw, "eadj": e_adj_raw, "f": f_raw, "ni": ni_raw, 
                                "c": c_raw, "d": d_raw, "s": s_raw, "ca": ca_hist, "cl": cl_hist, "assets": assets, "liabs": liabs
                            }
                        })
                    except Exception as q_e:
                        print("Error extracting q_anchor:", q_e)
            
            if temp_q_anchors:
                # Build TTM from temp_q_anchors
                ttm = temp_q_anchors[0].copy()
                ttm["year"] = "TTM"
                
                if len(temp_q_anchors) == 4:
                    # We have 4 quarters, sum flows
                    r_ttm = sum(q["_raw"]["r"] for q in temp_q_anchors)
                    e_ttm = sum(q["_raw"]["e"] for q in temp_q_anchors)
                    eadj_ttm = sum(q["_raw"]["eadj"] for q in temp_q_anchors)
                    f_ttm = sum(q["_raw"]["f"] for q in temp_q_anchors)
                    ni_ttm = sum(q["_raw"]["ni"] for q in temp_q_anchors)
                    
                    ttm["revenue_b"] = round(r_ttm / 1e9, 2)
                    ttm["eps"] = round(e_ttm, 2)
                    ttm["eps_adj"] = round(eadj_ttm, 2)
                    ttm["fcf_b"] = round(f_ttm / 1e9, 2)
                    ttm["net_income_b"] = round(ni_ttm / 1e9, 2)
                    
                    m_ttm = (ni_ttm / r_ttm * 100.0) if r_ttm > 0 else None
                    fcf_m_ttm = (f_ttm / r_ttm * 100.0) if r_ttm > 0 else None
                    
                    ttm["net_margin_pct"] = f"{m_ttm:.1f}%" if m_ttm is not None else "N/A"
                    ttm["gaap_net_margin_pct"] = f"{m_ttm:.1f}%" if m_ttm is not None else "N/A"
                    ttm["fcf_margin_pct"] = f"{fcf_m_ttm:.1f}%" if fcf_m_ttm is not None else "N/A"
                    
                    ast = temp_q_anchors[0]["_raw"]["assets"]
                    lbl = temp_q_anchors[0]["_raw"]["liabs"]
                    roic_ttm = (ni_ttm / (ast - lbl) * 100.0) if (ast and lbl and (ast - lbl) > 0) else None
                    ttm["roic_pct"] = f"{roic_ttm:.1f}%" if roic_ttm is not None else "N/A"
                else:
                    if historical_anchors:
                        ttm = historical_anchors[0].copy()
                        ttm["year"] = "TTM"
                        
                quarterly_anchors.append(ttm)
                
                # Remove _raw and append the rest
                for q in temp_q_anchors:
                    q.pop("_raw", None)
                    quarterly_anchors.append(q)
            elif historical_anchors:
                ttm = historical_anchors[0].copy()
                ttm["year"] = "TTM"
                quarterly_anchors.append(ttm)
                
        except Exception as e_q:
            print("Quarterly extraction error:", e_q)
\n"""
        
        lines = lines[:start_idx] + [new_q_anchors] + lines[end_idx:]
        with open('scraper/yahoo.py', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print("yahoo.py patched for TTM and EPS Adj")
    else:
        print("Could not find the target block to replace.")

except Exception as e:
    print("Error:", e)
