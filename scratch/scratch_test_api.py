from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)
response = client.get("/api/valuation/AAPL")
print("Status:", response.status_code)
if response.status_code != 200:
    print(response.json())
