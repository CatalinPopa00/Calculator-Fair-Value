from api.scraper.yahoo import get_analyst_data
import json

data = get_analyst_data("AAPL")
print(json.dumps(data.get("eps_estimates", []), indent=2))
print("---")
print(json.dumps(data.get("rev_estimates", []), indent=2))
