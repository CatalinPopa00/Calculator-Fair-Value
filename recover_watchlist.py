import sys
import os
sys.path.append(os.getcwd())
try:
    from api.utils.kv import kv_set, kv_get
    
    current = kv_get("watchlist") or []
    recovered = ["LLY", "JNJ", "PFE", "UNH", "ABBV", "MRK", "TMO", "ABT", "AZN", "DHR", "ACN", "V", "AMAT"]
    merged = list(set(current + recovered))
    
    success = kv_set("watchlist", merged)
    print(f"Watchlist recovered! New total: {len(merged)}")
    print(f"Status: {'Success' if success else 'Failed'}")
except Exception as e:
    print(f"Recovery Error: {e}")
