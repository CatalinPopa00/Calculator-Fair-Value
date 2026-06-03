import traceback
from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)
try:
    r = client.get('/api/valuation/ADBE')
    print(r.status_code, r.text[:500])
except Exception as e:
    traceback.print_exc()
