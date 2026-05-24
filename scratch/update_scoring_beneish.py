import os
import re

filepath = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value\models\scoring.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

beneish_func = '''
def calculate_beneish_m_score(metrics):
    industry = (metrics.get('industry') or "").lower()
    sector = (metrics.get('sector') or "").lower()
    is_fin = 'financial' in sector
    is_reit = 'real estate' in sector or 'reit' in sector
    
    if is_fin or is_reit:
        return {"m_score": None, "label": "N/A (Not Applicable for Financials/REITs)", "status": "neutral"}
        
    beneish = metrics.get('beneish_data')
    if not beneish or not beneish.get('current') or not beneish.get('prev'):
        return {"m_score": None, "label": "N/A - Incomplete Data", "status": "neutral"}
        
    curr = beneish['current']
    prev = beneish['prev']
    
    def safe_div(n, d):
        if d is None or n is None or d == 0: return None
        return float(n) / float(d)
        
    try:
        # 1. DSRI = (Net Receivables_current / Sales_current) / (Net Receivables_prev / Sales_prev)
        dsri = safe_div(safe_div(curr['net_receivables'], curr['sales']), safe_div(prev['net_receivables'], prev['sales']))
        
        # 2. GMI = Gross Margin_prev / Gross Margin_current
        gmi = safe_div(safe_div(prev['gross_profit'], prev['sales']), safe_div(curr['gross_profit'], curr['sales']))
        
        # 3. AQI = [1 - (Current Assets_current + PP&E_current) / Total Assets_current] / [1 - (Current Assets_prev + PP&E_prev) / Total Assets_prev]
        def get_aqi_part(ca, ppe, ta):
            if ca is None or ppe is None or ta is None or ta == 0: return None
            return 1 - ((float(ca) + float(ppe)) / float(ta))
        aqi = safe_div(get_aqi_part(curr['current_assets'], curr['ppe'], curr['total_assets']), get_aqi_part(prev['current_assets'], prev['ppe'], prev['total_assets']))
        
        # 4. SGI = Sales_current / Sales_prev
        sgi = safe_div(curr['sales'], prev['sales'])
        
        # 5. DEPI = Depreciation Rate_prev / Depreciation Rate_current
        def get_dep_rate(dep, ppe):
            if dep is None or ppe is None or (float(dep) + float(ppe)) == 0: return None
            return float(dep) / (float(dep) + float(ppe))
        depi = safe_div(get_dep_rate(prev['depreciation'], prev['ppe']), get_dep_rate(curr['depreciation'], curr['ppe']))
        
        # 6. SGAI = (SGA_current / Sales_current) / (SGA_prev / Sales_prev)
        sgai = safe_div(safe_div(curr['sga'], curr['sales']), safe_div(prev['sga'], prev['sales']))
        
        # 7. LVGI = Leverage_current / Leverage_prev
        def get_leverage(cl, ltd, ta):
            if cl is None or ltd is None or ta is None or ta == 0: return None
            return (float(cl) + float(ltd)) / float(ta)
        lvgi = safe_div(get_leverage(curr['current_liabilities'], curr['long_term_debt'], curr['total_assets']), get_leverage(prev['current_liabilities'], prev['long_term_debt'], prev['total_assets']))
        
        # 8. TATA = (Net Income_current - CFO_current) / Total Assets_current
        tata = None
        if curr['net_income_cont'] is not None and curr['cfo'] is not None and curr['total_assets'] and float(curr['total_assets']) > 0:
            tata = (float(curr['net_income_cont']) - float(curr['cfo'])) / float(curr['total_assets'])
            
        vars = [dsri, gmi, aqi, sgi, depi, sgai, lvgi, tata]
        if any(v is None for v in vars):
            return {"m_score": None, "label": "N/A - Incomplete Data", "status": "neutral"}
            
        m_score = -4.84 + (0.92 * dsri) + (0.528 * gmi) + (0.404 * aqi) + (0.892 * sgi) + (0.115 * depi) - (0.172 * sgai) + (4.679 * tata) - (0.327 * lvgi)
        
        if m_score < -1.78:
            return {"m_score": round(m_score, 2), "label": "Pass: Low Risk of Manipulation", "status": "pass"}
        else:
            return {"m_score": round(m_score, 2), "label": "Fail: High Risk of Manipulation", "status": "fail"}
    except Exception as e:
        return {"m_score": None, "label": "N/A - Calculation Error", "status": "neutral"}

'''

health_func = '''def calculate_health_score(metrics):
    res = calculate_scoring_reform({"margin_of_safety": 0}, metrics)
    b_score = calculate_beneish_m_score(metrics)
    tot = res["health_score_total"]
    if b_score.get("status") == "fail":
        tot = max(0, tot - 20)
    return {"total": tot, "breakdown": res["health_breakdown"], "beneish": b_score}
'''

# Replace calculate_health_score
pattern_health = r'def calculate_health_score\(metrics\):.*?return \{"total": res\["health_score_total"\], "breakdown": res\["health_breakdown"\]\}'
content = re.sub(pattern_health, health_func, content, flags=re.DOTALL)

# Insert beneish_func right before calculate_health_score
content = content.replace("def calculate_health_score", beneish_func + "def calculate_health_score")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated scoring.py with beneish")
