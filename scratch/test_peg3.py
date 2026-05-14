import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from index import get_valuation

class DummyResponse:
    def __init__(self):
        self.headers = {}

try:
    res = get_valuation("ADBE", DummyResponse())
    with open(os.path.join(os.path.dirname(__file__), "test_adbe_val.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("Saved to test_adbe_val.json")
except Exception as e:
    import traceback
    traceback.print_exc()
