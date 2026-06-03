from fastapi.testclient import TestClient
from api.index import app
import json

client = TestClient(app)
r = client.get('/api/fairvalue?ticker=IREN')
data = r.json()
print("scoring_results:", json.dumps(data.get('scoring_results', {}), indent=2))
print("val_data:", json.dumps(data.get('valuation_data', {}), indent=2))
