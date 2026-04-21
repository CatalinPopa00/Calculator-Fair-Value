import json
import traceback

try:
    from scraper.yahoo import get_company_data
    
    data = get_company_data("AAPL", fast_mode=False)

    print("Historical Anchors:")
    for anchor in data.get("historical_anchors", []):
        print(anchor)
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
