import sys
import os
sys.path.append(os.path.dirname(__file__))

from api.index import app
from fastapi.testclient import TestClient

client = TestClient(app)

response = client.get("/api/valuation/AAPL")
print(response.status_code)
print(response.json())
