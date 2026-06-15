import requests
import json

headers = {
    "x-rapidapi-key": "6bcecd8213msh7a7cd918149f69bp1a3892jsn276c6622e2fd",
    "x-rapidapi-host": "mboum-finance.p.rapidapi.com"
}

url = "https://mboum-finance.p.rapidapi.com/v10/finance/quoteSummary/META?modules=earningsTrend"
resp = requests.get(url, headers=headers)
with open("test_mboum.json", "w", encoding="utf-8") as f:
    f.write(json.dumps(resp.json(), indent=2))

print("Saved to test_mboum.json")
