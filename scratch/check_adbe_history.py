from api.scraper.yahoo import get_company_data
import json

data = get_company_data("ADBE", fast_mode=False)

print("Adjusted EPS from Yahoo:", data.get("adjusted_eps"))
print("Current Price:", data.get("current_price"))

print("\nHistorical Anchors:")
for anchor in data.get("historical_anchors"):
    print(anchor)

print("\nHistorical Trends:")
for t in data.get("historical_trends"):
    print(t)
