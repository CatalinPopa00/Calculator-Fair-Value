import sys
import os
import json
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.index import app
import utils.kv

# MOCK VERCEL KV IN-MEMORY
mock_kv_store = {}

def mock_kv_get(key):
    return mock_kv_store.get(key)

def mock_kv_set(key, value, ex=None):
    mock_kv_store[key] = value
    return True

utils.kv.kv_get = mock_kv_get
utils.kv.kv_set = mock_kv_set
# Also patch the ones imported directly in api.index
import api.index
api.index.kv_get = mock_kv_get
api.index.kv_set = mock_kv_set

client = TestClient(app)

def test_accumulator():
    ticker = "ADBE"
    accum_key = f"accum_history_v2_{ticker}"
    
    # 1. Inject fake historical data for year 2021
    fake_data = [
        {
            "year": "2021",
            "revenue_b": 15.78,
            "eps": 10.04,
            "fcf_b": 6.88
        }
    ]
    res = utils.kv.kv_set(accum_key, fake_data, ex=None)
    print(f"Injected fake 2021 data into KV cache. Success: {res}")
    
    # Let's also verify kv_get works right after
    check_get = utils.kv.kv_get(accum_key)
    print(f"Check kv_get right after set: {check_get}")
    
    # 2. Call the valuation endpoint with fast_mode=false to fetch real anchors
    print(f"Calling /api/valuation/{ticker}...")
    response = client.get(f"/api/valuation/{ticker}?fast_mode=false&force_refresh=true")
    
    if response.status_code == 200:
        data = response.json()
        anchors = data.get("historical_anchors", [])
        print(f"\n--- Accumulator Results (Count: {len(anchors)}) ---")
        for a in anchors:
            print(f"Year: {a.get('year')}, Rev: {a.get('revenue_b')}, EPS: {a.get('eps')}")
            
        # Verify 2021 is present
        has_2021 = any(str(a.get('year')) == "2021" for a in anchors)
        if has_2021:
            print("\nSUCCESS: 2021 data was successfully accumulated and merged!")
        else:
            print("\nFAILURE: 2021 data is missing from the output.")
    else:
        print(f"Endpoint failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_accumulator()
