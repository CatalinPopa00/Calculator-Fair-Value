import sys
import os
import requests

# Assuming the app is running locally or we can just import the app and test via TestClient
from fastapi.testclient import TestClient
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.index import app

client = TestClient(app)

def test_api():
    response = client.get("/api/sector-peers/NOW")
    data = response.json()
    for p in data:
        print(f"Ticker: {p.get('ticker')}")
        print(f"  forward_pe: {p.get('forward_pe')}")
        print(f"  forward_ev_ebitda: {p.get('forward_ev_ebitda')}")
        print(f"  forward_ev_sales: {p.get('forward_ev_sales')}")
        print("---")

if __name__ == "__main__":
    test_api()
