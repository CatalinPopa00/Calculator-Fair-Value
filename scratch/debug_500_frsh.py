
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scraper.yahoo import get_lightweight_company_data
import json

ticker = "FRSH"
try:
    data = get_lightweight_company_data(ticker)
    print(json.dumps(data, indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
