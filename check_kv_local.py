import sys
import os
sys.path.append(os.getcwd())
try:
    from api.utils.kv import kv_get
except ImportError:
    print("Could not import api.utils.kv")
    sys.exit(1)
import json

def check():
    watchlist = kv_get("watchlist")
    print("KV WATCHLIST:")
    print(json.dumps(watchlist, indent=2))
    
    overrides = kv_get("overrides")
    if overrides:
        print("\nKV OVERRIDES (Tickers found):")
        print(list(overrides.keys()))
    else:
        print("\nNo overrides found.")

if __name__ == "__main__":
    check()
