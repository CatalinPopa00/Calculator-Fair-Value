import sys
sys.path.append(r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value")
import json
from scraper.yahoo import get_company_data

res = get_company_data("RHM.DE")
print(json.dumps(res['metrics'], indent=2))
