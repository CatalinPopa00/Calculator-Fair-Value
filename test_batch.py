
import requests
import json

# Simulate a watchlist
watchlist = ["GOOGL", "AMAT", "MRK", "AAPL"]
url = "http://127.0.0.1:8000/api/batch-valuation"
# Or if local dev is on a different port, adjust. 
# Since I can't know the exact local port, I'll test the logic by calling the python functions directly.

import sys
import os
sys.path.append(os.getcwd())
from api.index import get_valuation

for t in watchlist:
    print(f"Testing {t}...")
    res = get_valuation(t)
    if "error" in res:
        print(f"  FAILED: {res['error']}")
    else:
        print(f"  SUCCESS: Fair Val={res.get('fair_value')}")
