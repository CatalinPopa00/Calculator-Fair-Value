import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from index import process_ticker
import json

res = process_ticker("CELH")
with open(os.path.join(os.path.dirname(__file__), "test_celh.json"), "w") as f:
    json.dump(res, f, indent=2)
print("Saved to test_celh.json")
