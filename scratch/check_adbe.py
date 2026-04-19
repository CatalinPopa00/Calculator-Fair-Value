import requests
import json

ticker = "ADBE"
url = f"http://127.0.0.1:8000/api/analyst/{ticker}"

try:
    resp = requests.get(url)
    data = resp.json()
    print(f"Version: {data.get('_v', 'unknown')}")
    
    eps_est = data.get("eps_estimates", [])
    for e in eps_est:
        if "FY 2026" in e.get("period", ""):
            print(f"FY 2026: Avg={e.get('avg')}, Growth={e.get('growth')}")
             
except Exception as e:
    print(f"Error: {e}")
