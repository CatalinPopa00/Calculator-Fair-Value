import sys
import os
sys.path.append(os.getcwd())
from api.scraper.yahoo import get_company_data
import json

ticker = "PLTR"
data = get_company_data(ticker, fast_mode=False)

print("\nAdjusted History Debug:")
# Since I added a print in yahoo.py, it should show up in the command output.
# But I'll also check the final returned object.
print("Adjusted EPS:", data.get("adjusted_eps"))

for anchor in data.get("historical_anchors", []):
    if "2025" in str(anchor.get("year")):
        print(f"2025 Anchor: {anchor}")

print("\nHistorical Data years:", data.get("historical_data", {}).get("years"))
print("Historical Data eps:", data.get("historical_data", {}).get("eps"))
