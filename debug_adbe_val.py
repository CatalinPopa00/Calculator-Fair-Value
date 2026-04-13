import sys
import os
import json
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), 'api'))
from api.index import app

client = TestClient(app)
response = client.get("/api/valuation/ADBE")
with open("adbe_valuation.json", "w") as f:
    json.dump(response.json(), f, indent=2)
print("Saved to adbe_valuation.json")
