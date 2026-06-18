import sys
sys.path.append('.')
from scraper.yahoo import get_ownership_data

data = get_ownership_data("AAPL")
roster = data.get("insider_roster", [])
print(f"Found {len(roster)} insiders in roster")
for r in roster:
    print(r)
