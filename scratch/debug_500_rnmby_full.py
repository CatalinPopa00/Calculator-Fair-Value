
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scraper.yahoo import get_company_data
import json

ticker = "RNMBY"
try:
    data = get_company_data(ticker)
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
