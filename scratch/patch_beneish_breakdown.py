import os

filepath = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value\models\scoring.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the end of calculate_beneish_m_score
old_code = '''        if m_score < -1.78:
            return {"m_score": round(m_score, 2), "label": "Pass: Low Risk of Manipulation", "status": "pass"}
        else:
            return {"m_score": round(m_score, 2), "label": "Fail: High Risk of Manipulation", "status": "fail"}'''

new_code = '''        breakdown = [
            {"metric": "DSRI (Days Sales in Receivables)", "value": round(dsri, 4), "threshold": "> 1.0 indicates inflated revenues", "status": "fail" if dsri > 1.2 else "pass"},
            {"metric": "GMI (Gross Margin Index)", "value": round(gmi, 4), "threshold": "> 1.0 indicates deteriorating margins", "status": "fail" if gmi > 1.1 else "pass"},
            {"metric": "AQI (Asset Quality Index)", "value": round(aqi, 4), "threshold": "> 1.0 indicates increased cost deferral", "status": "fail" if aqi > 1.1 else "pass"},
            {"metric": "SGI (Sales Growth Index)", "value": round(sgi, 4), "threshold": "> 1.0 means growing sales (can be an incentive to manipulate)", "status": "neutral"},
            {"metric": "DEPI (Depreciation Index)", "value": round(depi, 4), "threshold": "> 1.0 indicates assets depreciating slower", "status": "fail" if depi > 1.1 else "pass"},
            {"metric": "SGAI (Sales, General & Admin Index)", "value": round(sgai, 4), "threshold": "> 1.0 indicates decreasing administrative efficiency", "status": "fail" if sgai > 1.1 else "pass"},
            {"metric": "LVGI (Leverage Index)", "value": round(lvgi, 4), "threshold": "> 1.0 indicates increasing leverage", "status": "fail" if lvgi > 1.1 else "pass"},
            {"metric": "TATA (Total Accruals to Total Assets)", "value": round(tata, 4), "threshold": "Higher positive value indicates higher accruals (risk)", "status": "fail" if tata > 0.05 else "pass"}
        ]
        
        if m_score < -1.78:
            return {"m_score": round(m_score, 2), "label": "Pass: Low Risk of Manipulation", "status": "pass", "breakdown": breakdown}
        else:
            return {"m_score": round(m_score, 2), "label": "Fail: High Risk of Manipulation", "status": "fail", "breakdown": breakdown}'''

content = content.replace(old_code, new_code)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated models/scoring.py to include Beneish breakdown!")
