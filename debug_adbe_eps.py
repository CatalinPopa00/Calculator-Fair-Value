import sys
import os
import json

sys.path.append(os.path.join(os.getcwd(), 'api'))
from scraper.yahoo import get_analyst_data

data = get_analyst_data("ADBE")
print("EPS:")
print(json.dumps(data.get('eps_estimates'), indent=2))
print("REV:")
print(json.dumps(data.get('rev_estimates'), indent=2))
