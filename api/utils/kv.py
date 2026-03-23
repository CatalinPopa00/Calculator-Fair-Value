import os
import requests
import json

KV_REST_API_URL = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")

def kv_get(key: str):
    if not KV_REST_API_URL or not KV_REST_API_TOKEN:
        return None
    try:
        url = KV_REST_API_URL.rstrip('/')
        headers = {
            "Authorization": f"Bearer {KV_REST_API_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = ["GET", key]
        resp = requests.post(url, headers=headers, json=payload, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("result")
            if data:
                try:
                    return json.loads(data)
                except:
                    return data
    except Exception as e:
        print(f"KV GET Error: {e}")
    return None

def kv_set(key: str, value, ex=None) -> bool:
    if not KV_REST_API_URL or not KV_REST_API_TOKEN:
        return False
    try:
        url = KV_REST_API_URL.rstrip('/')
        headers = {
            "Authorization": f"Bearer {KV_REST_API_TOKEN}",
            "Content-Type": "application/json"
        }
        # If ex is provided, use SET key value EX seconds
        if ex:
             payload = ["SET", key, json.dumps(value), "EX", str(ex)]
        else:
             payload = ["SET", key, json.dumps(value)]
             
        resp = requests.post(url, headers=headers, json=payload, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"KV SET Error: {e}")
    return False
