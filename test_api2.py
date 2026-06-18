from fastapi.testclient import TestClient
from api.index import app, CACHE_VERSION, valuation_cache
import logging

logging.basicConfig(level=logging.DEBUG)
cache_key = f"sector_peers_v1_FISV_{CACHE_VERSION}"
if cache_key in valuation_cache:
    print("In cache!", valuation_cache[cache_key])
    del valuation_cache[cache_key]

client = TestClient(app)
response = client.get("/api/sector-peers/FISV")
print(response.status_code)
print(response.json())
