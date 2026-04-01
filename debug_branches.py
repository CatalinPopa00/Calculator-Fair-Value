import sys
import os

# Add the root directory to sys.path
sys.path.append(os.getcwd())

# Mock KV
os.environ["KV_URL"] = "redis://localhost:6379"

from api.index import get_valuation

def test_debug_branches():
    ticker = "NVO"
    print(f"Testing valuation branches for {ticker}...")
    try:
        data = get_valuation(ticker)
        dcf = data["formula_data"]["dcf"]["5yr"]
        print(f"--- NVO DCF (5yr) ---")
        print(f"Perpetual Value: ${dcf['dcf_perpetual']['fair_value_per_share']}")
        print(f"Multiple Value:  ${dcf['dcf_exit_multiple']['fair_value_per_share']}")
        print(f"---")
        
        # Also check card-level assumptions
        print(f"Recommended Multi: {data['recommended_exit_multiple']}")
        print(f"DCF Assumptions Multi: {data['dcf_assumptions']['recommended_exit_multiple']}")
        
    except Exception as e:
        print(f"CRASH DETECTED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_debug_branches()
