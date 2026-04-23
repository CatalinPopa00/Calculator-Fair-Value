import sys
import os
sys.path.append(os.getcwd())
from utils.kv import kv_get
import json

def test():
    print("Testing kv_get('watchlist')...")
    try:
        val = kv_get("watchlist")
        print("Result:", val)
    except Exception as e:
        print("Error:", e)

    print("\nTesting kv_get('overrides')...")
    try:
        val = kv_get("overrides")
        print("Result:", "Dict with keys: " + str(list(val.keys())) if val else val)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
