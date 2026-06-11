import sys
import os
sys.path.append(os.path.dirname(__file__))

from api.index import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test article bypass
test_url = "https://finance.yahoo.com/news/apple-inc-aapl-stock-drops-140000030.html"
response = client.get(f"/api/article-bypass?url={test_url}")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print(f"HTML Length: {len(response.text)}")
    print("Success!")
else:
    print("Failed")
