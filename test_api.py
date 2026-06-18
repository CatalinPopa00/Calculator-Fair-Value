from fastapi.testclient import TestClient
from api.index import app
client = TestClient(app)
response = client.get("/api/sector-peers/FISV")
print(response.status_code)
print(response.json())
