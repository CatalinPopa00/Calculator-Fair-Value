import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scraper.yahoo import get_company_data

print("Fetching data for ADBE...")
data = get_company_data("ADBE", fast_mode=True, force_refresh=True)

print("Keys in data:", data.keys())
print("historical_anchors:", data.get("historical_anchors"))
