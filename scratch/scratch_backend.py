import sys
sys.path.append('.')
from api.index import get_company_data

data = get_company_data("AAPL", fast_mode=True, force_refresh=True)
if data and "ownership" in data:
    roster = data["ownership"].get("insider_roster", [])
    print(f"Found {len(roster)} insiders in roster")
    for r in roster:
        print(r)
else:
    print("No ownership data found in response")
