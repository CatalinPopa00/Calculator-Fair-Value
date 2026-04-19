import requests
import json

ticker = "MSFT"
url = f"http://127.0.0.1:8000/api/analyst/{ticker}"

try:
    resp = requests.get(url)
    print(f"Status: {resp.status_code}")
    data = resp.json()
    
    eps_est = data.get("eps_estimates", [])
    for e in eps_est:
        if "FY 2025" in e.get("period", ""):
             print(f"FY 2025: Avg={e.get('avg')}, Growth={e.get('growth')}")
        if "FY 2026" in e.get("period", ""):
            print(f"FY 2026: Avg={e.get('avg')}, Growth={e.get('growth')}")
             
except Exception as e:
    print(f"Error: {e}")
