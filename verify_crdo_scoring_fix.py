import sys
import os
from api.models.scoring import calculate_scoring_reform

# Mock data similar to CRDO screenshot
valuation_data = {
    "margin_of_safety": -24.3
}
metrics = {
    "sector": "Technology",
    "revenue_growth": "2.0%",
    "pe_ratio": "52.33x",
    "ev_to_ebitda": "46.48x",
    "ps_ratio": "16.45x",
    "peg_ratio": "1.74x",
    "debt_to_equity": 0.5,
    "interest_coverage": 15.0,
    "current_ratio": 2.1,
    "ebit_margin": 12.0,
    "roic": 10.0,
    "fcf_trend": "Growing"
}

res = calculate_scoring_reform(valuation_data, metrics)

print(f"Buy Score: {res['good_to_buy_total']}/100")
for item in res['buy_breakdown']:
    print(f"- {item['metric']}: {item['value']} -> {item['points_awarded']} pts")

# Specifically check PEG ratio
peg_item = next((i for i in res['buy_breakdown'] if "PEG" in i['metric']), None)
if peg_item and peg_item['points_awarded'] > 0:
    print("\nSUCCESS: PEG points awarded for '1.74x' string!")
else:
    print("\nFAILURE: No points awarded for PEG '1.74x'. Check clean_ratio logic.")
