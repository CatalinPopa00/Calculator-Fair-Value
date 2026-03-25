import os
import requests
import json

KV_REST_API_URL = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")

def list_keys():
    if not KV_REST_API_URL or not KV_REST_API_TOKEN:
        print("Missing KV credentials")
        return
    
    url = KV_REST_API_URL.rstrip('/')
    headers = {"Authorization": f"Bearer {KV_REST_API_TOKEN}"}
    
    # Try SCAN 0
    payload = ["SCAN", "0", "COUNT", "1000"]
    resp = requests.post(url, headers=headers, json=payload)
    
    if resp.status_code == 200:
        result = resp.json().get("result")
        if result and len(result) >= 2:
            cursor, keys = result
            print(f"Found {len(keys)} keys:")
            relevant_tickers = set()
            for k in keys:
                if k.startswith("v_res_"):
                    parts = k.split("_")
                    if len(parts) >= 3:
                        relevant_tickers.add(parts[2])
                print(f" - {k}")
            
            print("\nIDENTIFIED TICKERS FROM CACHE:")
            print(sorted(list(relevant_tickers)))
    else:
        print(f"Error: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    list_keys()
