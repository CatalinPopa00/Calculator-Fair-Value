from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.getcwd())
from api.index import app
import json

client = TestClient(app)

def test_endpoints():
    print("Testing /api/watchlist...")
    try:
        response = client.get("/api/watchlist")
        print("Status Code:", response.status_code)
        print("Response Body:", response.text)
    except Exception as e:
        print("Error calling /api/watchlist:", e)

    print("\nTesting /api/overrides...")
    try:
        response = client.get("/api/overrides")
        print("Status Code:", response.status_code)
        print("Response Body:", response.text)
    except Exception as e:
        print("Error calling /api/overrides:", e)

if __name__ == "__main__":
    test_endpoints()
