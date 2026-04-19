import requests

ticker = "ADBE"
url = f"http://127.0.0.1:8000/api/valuation/{ticker}"

try:
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()
    lynch = data.get("valuation", {}).get("peter_lynch", {})
    
    print(f"Ticker: {ticker}")
    print(f"Price: {data.get('metrics', {}).get('current_price')}")
    print(f"EPS: {lynch.get('trailing_eps')}")
    print(f"Growth: {lynch.get('eps_growth_estimated')}")
    print(f"FV (PE Historic): {lynch.get('fair_value')}")
    print(f"FV (PE 20): {lynch.get('fair_value_pe_20')}")

except Exception as e:
    print(f"Error: {e}")
