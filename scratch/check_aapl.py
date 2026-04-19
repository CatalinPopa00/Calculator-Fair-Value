import requests

ticker = "AAPL"
url = f"http://127.0.0.1:8000/api/analyst/{ticker}"

try:
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()
    print(f"Ticker: {ticker}")
    print(f"Version: {data.get('_v')}")
    
    eps = data.get("eps_estimates", [])
    for e in eps:
        if "FY" in e["period"]:
            print(f"{e['period']}: Avg={e['avg']}, Growth={e.get('growth')}")

except Exception as e:
    print(f"Error: {e}")
