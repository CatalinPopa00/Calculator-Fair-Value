import sys
import os

# Add the root directory to sys.path
sys.path.append(os.getcwd())

# Mock KV
import os
os.environ["KV_URL"] = "redis://localhost:6379"

from api.index import get_valuation

def test_debug():
    ticker = "NVO"
    print(f"Testing valuation for {ticker}...")
    try:
        data = get_valuation(ticker)
        print("Success!")
        # print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"CRASH DETECTED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_debug()
