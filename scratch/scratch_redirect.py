from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)
response = client.get("/api/article-bypass?url=https://www.wsj.com/articles/a-great-stock-market-rally-meets-a-big-bump-f6110f27", allow_redirects=False)
print("Status:", response.status_code)
if response.status_code in [301, 302]:
    print("Redirect Location:", response.headers.get("location"))
else:
    print(response.text[:500])
