import traceback
from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)
try:
    r = client.get('/api/valuation/V')
    data = r.json()
    print("Archetype:", data.get("archetype"))
    print("Weights:", data.get("archetype_weights"))
except Exception as e:
    traceback.print_exc()
