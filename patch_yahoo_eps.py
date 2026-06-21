import re

try:
    with open('scraper/yahoo.py', 'r', encoding='utf-8') as f:
        yahoo = f.read()

    old_code = """                        # Fetch Normalized EPS for Adjusted EPS
                        e_adj_raw = get_q_is_metric('Normalized EPS', q_col)
                        if e_adj_raw is None:
                            e_adj_raw = e_raw"""

    new_code = """                        # Fetch Normalized Income / Shares for Adjusted EPS
                        norm_inc = get_q_is_metric('Normalized Income', q_col)
                        if norm_inc is not None and s_raw and s_raw > 0:
                            e_adj_raw = norm_inc / s_raw
                        else:
                            e_adj_raw = get_q_is_metric('Normalized EPS', q_col)
                            if e_adj_raw is None:
                                e_adj_raw = e_raw"""
    
    if old_code in yahoo:
        yahoo = yahoo.replace(old_code, new_code)
        with open('scraper/yahoo.py', 'w', encoding='utf-8') as f:
            f.write(yahoo)
        print("yahoo.py EPS Adj calculation patched")
    else:
        print("Could not find the target EPS Adj block.")
except Exception as e:
    print("Error:", e)
