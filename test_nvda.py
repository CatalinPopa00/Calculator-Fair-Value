from scraper.yahoo import get_company_data
from models.scoring import calculate_beneish_m_score
import json

data = get_company_data("NVDA", fast_mode=False, force_refresh=True)
metrics = data.get('metrics', {})

beneish_data = metrics.get('beneish_data')
print("Extracted beneish data for NVDA:")
print(json.dumps(beneish_data, indent=2))

res = calculate_beneish_m_score(metrics)
print("Score result:", json.dumps(res, indent=2))
