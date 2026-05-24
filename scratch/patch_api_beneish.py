import os
import re

filepath = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value\api\index.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace the health score assignment logic
old_scoring = '''        scoring_results = calculate_scoring_reform({"margin_of_safety": safe_mos, "sector_median_peg": safe_median_peg}, data)
        
        health_score_total = scoring_results.get("health_score_total")
        health_breakdown = scoring_results.get("health_breakdown")
        
        good_to_buy_total = scoring_results.get("good_to_buy_total")
        buy_breakdown = scoring_results.get("buy_breakdown")'''

new_scoring = '''        from models.scoring import calculate_health_score
        scoring_results = calculate_scoring_reform({"margin_of_safety": safe_mos, "sector_median_peg": safe_median_peg}, data)
        
        health_results = calculate_health_score(data)
        health_score_total = health_results.get("total")
        health_breakdown = health_results.get("breakdown")
        beneish_data = health_results.get("beneish")
        
        good_to_buy_total = scoring_results.get("good_to_buy_total")
        buy_breakdown = scoring_results.get("buy_breakdown")'''

content = content.replace(old_scoring, new_scoring)

# 2. Add health_score: { beneish: ... } to the JSON payload
old_payload = '''            "historical_anchors": historical_anchors,
            "company_overview_synthesis": data.get("company_overview_synthesis"),
            "health_score_total": health_score_total,
            "health_breakdown": health_breakdown,
            "good_to_buy_total": good_to_buy_total,'''

new_payload = '''            "historical_anchors": historical_anchors,
            "company_overview_synthesis": data.get("company_overview_synthesis"),
            "health_score_total": health_score_total,
            "health_breakdown": health_breakdown,
            "health_score": { "beneish": beneish_data },
            "good_to_buy_total": good_to_buy_total,'''

content = content.replace(old_payload, new_payload)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated api/index.py to expose Beneish M-Score and properly penalize health score!")
