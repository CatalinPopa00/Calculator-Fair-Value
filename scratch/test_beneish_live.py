import sys
import json
sys.path.append(r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value")
from scraper.yahoo import get_company_data
from models.scoring import calculate_health_score

res = get_company_data("RHM.DE")
print("Beneish Data Extraction:")
print(json.dumps(res.get('beneish_data', {}), indent=2))

metrics = res
health_res = calculate_health_score(metrics)
print("\nBeneish Result from scoring:")
print(json.dumps(health_res.get('beneish', {}), indent=2))
