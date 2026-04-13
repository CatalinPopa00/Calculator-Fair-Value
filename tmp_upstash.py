import requests
import json
import os

# Create dummy URL and TOKEN to test logic (I will pass them via env or print the expected payload)
# Even if it fails, I want to see what is generated.
def test_upstash_payload():
    url = "https://example-upstash.io"
    headers = {"Authorization": "Bearer TEST", "Content-Type": "application/json"}
    
    # Test watchlist format
    watchlist = ["AAPL", "TSLA"]
    payload_w = ["SET", "watchlist", json.dumps(watchlist)]
    print("Watchlist Payload:", json.dumps(payload_w))

    # Test overrides format
    overrides = {
        "AAPL": {
            "inputs": {"fcf-source": "custom"},
            "toggles": {},
            "computed": {}
        }
    }
    payload_o = ["SET", "overrides", json.dumps(overrides)]
    print("Overrides Payload:", json.dumps(payload_o))

test_upstash_payload()
