import sys
import os
import json
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), 'api'))
from api.index import app

client = TestClient(app)
response = client.get("/api/analyst/ADBE")
with open("adbe_analyst_api_response.json", "w") as f:
    json.dump(response.json(), f, indent=2)
print("Saved to adbe_analyst_api_response.json")
