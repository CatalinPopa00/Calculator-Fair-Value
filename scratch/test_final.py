
import sys
import os
sys.path.append(os.getcwd())

from scraper.yahoo import get_company_data
import json

try:
    print("Fetching ADBE...")
    data = get_company_data("ADBE", fast_mode=True)
    # v71+: Verify the historical anchors
    anchors = data.get("historical_anchors", [])
    print("ANTIGRAVITY TEST RESULTS (Anchor EPS):")
    for a in anchors:
        print(f"Year {a['year']}: {a['eps']}")
    
    # v73+: Verify projections
    estimates = data.get("eps_estimates", [])
    print("\nANTIGRAVITY TEST RESULTS (Projections):")
    for e in estimates:
        print(f"{e['period']}: {e['avg']}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
