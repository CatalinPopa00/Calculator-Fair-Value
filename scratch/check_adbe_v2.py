import requests

ticker = "ADBE"
url = f"http://127.0.0.1:8000/api/analyst/{ticker}"

try:
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()
    print(f"Version: {data.get('_v', 'unknown')}")
    
    eps = data.get("eps_estimates", [])
    rev = data.get("rev_estimates", [])
    
    for e in eps:
        if "FY 2026" in e["period"]:
            print(f"EPS FY 2026: Avg={e['avg']}, Growth={e.get('growth')}")
            
    for r in rev:
        if "FY 2026" in r["period"]:
            print(f"REV FY 2026: Avg={r['avg']}, Growth={r.get('growth')}")

except Exception as e:
    print(f"Error: {e}")
