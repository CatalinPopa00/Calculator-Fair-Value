from api.index import app
from fastapi.testclient import TestClient

client = TestClient(app)

res = client.get("/api/sector-peers/FISV")
print(res.json())
