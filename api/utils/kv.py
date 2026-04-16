import os
import requests
import json
import time

KV_REST_API_URL = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")

# Local memory cache fallback (v2: with TTL support)
MEMORY_CACHE = {}

def kv_get(key: str):
    # Check memory cache first
    if key in MEMORY_CACHE:
        entry = MEMORY_CACHE[key]
        if entry["expiry"] is None or entry["expiry"] > time.time():
            return entry["value"]
        else:
            del MEMORY_CACHE[key]

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
            result = resp.json().get("result")
            if result is None:
                return None # Truly missing key
            try:
                data = json.loads(result)
            except:
                data = result
            
            # Populate memory cache for next time
            MEMORY_CACHE[key] = {"value": data, "expiry": None} # We don't know the redis TTL easily here
            return data
        else:
            print(f"KV API Error: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"KV GET Error: {e}")
        return None

def kv_set(key: str, value, ex=None) -> bool:
    # Update memory cache
    expiry = (time.time() + int(ex)) if ex else None
    MEMORY_CACHE[key] = {"value": value, "expiry": expiry}

    if not KV_REST_API_URL or not KV_REST_API_TOKEN:
        return True # Treat as success for local operation
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
