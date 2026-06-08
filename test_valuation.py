import sys
sys.path.append('.')
from api.index import app
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get("/api/valuation/RHM.DE")
data = response.json()
print(f"price: {data.get('current_price')}")
print(f"trailing_eps: {data.get('company_profile', {}).get('trailing_eps')}")
print(f"adjusted_eps: {data.get('company_profile', {}).get('adjusted_eps')}")
print(f"pe_ratio: {data.get('company_profile', {}).get('current_pe')}")
print(f"forward_pe: {data.get('company_profile', {}).get('fwd_pe')}")
print(f"eps_estimates: {data.get('eps_estimates')[0:2]}")
