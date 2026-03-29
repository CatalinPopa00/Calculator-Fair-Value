import os, sys, json
sys.path.insert(0, os.path.abspath('.'))
from api.index import get_valuation

res_fast = get_valuation('ADBE', None, True)
res_full = get_valuation('ADBE', None, False)

with open('debug_sync.txt', 'w') as f:
    f.write('--- FAST MODE ---\n')
    f.write(f'FV: {res_fast.get("fair_value")}, Health: {res_fast.get("health_score_total")}\n')
    
    # Calculate difference in keys
    f.write('\n== FAST COMPANY PROFILE ==\n')
    for k, v in res_fast.get('company_profile', {}).items():
        v_full = res_full.get('company_profile', {}).get(k)
        if v != v_full:
            f.write(f'{k}: {v} (Fast) vs {v_full} (Full)\n')
        
    f.write('\n--- FULL MODE ---\n')
    f.write(f'FV: {res_full.get("fair_value")}, Health: {res_full.get("health_score_total")}\n')
