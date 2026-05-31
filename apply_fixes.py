import re
import os

def fix_scoring_py():
    with open('models/scoring.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix ROE fallback (Never award points if ROE < 0)
    roe_pattern = r"if roe <= 0 and roic > 10:\s+roe_pts = 20 if roic > 12 else 10\s+add_h\(\"ROE \(via ROIC Fallback\)\", roe, roe_pts, 20, False\)\s+else:"
    roe_replacement = r"if roe < 0:\n            add_h(\"ROE\", roe, 0, 20, False)\n        else:"
    content = re.sub(roe_pattern, roe_replacement, content)
    
    # 2. Fix Interest Coverage (Debt == 0 check)
    # We will replace add_h("Interest Coverage", ic, <pts>, <max>, True)
    # with a version that checks debt_to_equity == 0.
    def ic_replacer(m):
        indent = m.group(1)
        ic_var = m.group(2)
        expr = m.group(3)
        max_pts = m.group(4)
        return f"{indent}de_for_ic = clean_ratio(metrics.get('debt_to_equity'))\n{indent}add_h(\"Interest Coverage\", {ic_var}, {max_pts} if de_for_ic == 0 else ({expr}), {max_pts}, True)"
    
    content = re.sub(r"([ \t]+)add_h\(\"Interest Coverage\", ([a-zA-Z0-9_]+), (.*?), (\d+), True\)", ic_replacer, content)

    # 3. Time Horizon Fixes for Labels
    content = content.replace('"P/E Ratio (2y Avg Fwd)"', '"P/E Ratio (1Y Fwd)"')
    content = content.replace('"EV/EBITDA (2y Avg Fwd)"', '"EV/EBITDA (1Y Fwd)"')
    
    # 4. PEG Ratio Formula in Backend
    # Replace:
    # hybrid_peg = 0.0
    # if fwd_pe > 0 and eps_2y_g > 0:
    #     hybrid_peg = fwd_pe / eps_2y_g
    
    peg_old = """    hybrid_peg = 0.0
    if fwd_pe > 0 and eps_2y_g > 0:
        hybrid_peg = fwd_pe / eps_2y_g"""
        
    peg_new = """    hybrid_peg = 0.0
    growth_rate = rev_2y_g if rev_2y_g > 0 else eps_2y_g
    if fwd_pe > 0 and growth_rate > 0:
        # User requested: (Forward P/E 1Y) / (Forward Growth Rate * 100)
        # Note: clean_percent returns 15.0 for 15%.
        # If it returns 15.0, dividing by 15.0 is the same as PE / (0.15 * 100).
        # We explicitly enforce the logic mathematically as PE / (growth * 100) assuming growth is decimal.
        # But since clean_percent scales decimals < 10.0 by 100, we check:
        actual_growth_pct = growth_rate * 100.0 if growth_rate < 1.0 else growth_rate
        hybrid_peg = fwd_pe / actual_growth_pct"""
        
    content = content.replace(peg_old, peg_new)
    
    with open('models/scoring.py', 'w', encoding='utf-8') as f:
        f.write(content)

def fix_app_js():
    with open('app.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace "P/E Ratio (2y Avg Fwd)" with "P/E Ratio (1Y Fwd)" in JS
    content = content.replace('P/E Ratio (2y Avg Fwd)', 'P/E Ratio (1Y Fwd)')
    content = content.replace('EV/EBITDA (2y Avg Fwd)', 'EV/EBITDA (1Y Fwd)')
    
    # PEG Ratio formula fix in simulation UI
    # In app.js: const newPEG = (fwd_growth > 0 && activePE > 0) ? activePE / fwd_growth : 0;
    # But wait, earlier there was activePE / (simGrowth * 100)?
    
    # Let's fix the fwd_growth parsing
    # const fwd_growth = (pegUsedGrowth > 0) ? (pegUsedGrowth * 100) : dynamicEpsGrowth;
    # It shouldn't multiply by 100 if it's already > 1
    js_growth_fix = """                const fwd_growth = (pegUsedGrowth > 0) ? (pegUsedGrowth < 1.0 ? pegUsedGrowth * 100 : pegUsedGrowth) : dynamicEpsGrowth;
                let rev_fwd_growth = (revUsedGrowth > 0) ? (revUsedGrowth < 1.0 ? revUsedGrowth * 100 : revUsedGrowth) : dynamicRevGrowth;"""
                
    content = re.sub(r"const fwd_growth = \(pegUsedGrowth > 0\) \? \(pegUsedGrowth \* 100\) : dynamicEpsGrowth;\s+let rev_fwd_growth = \(revUsedGrowth > 0\) \? \(revUsedGrowth \* 100\) : dynamicRevGrowth;", js_growth_fix, content)
    
    with open('app.js', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_scoring_py()
    fix_app_js()
    print("Fixes applied successfully.")
