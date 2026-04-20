import sys
import os

# Add the parent directory to sys.path to import the api module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.scraper.yahoo import get_company_data

ticker = "HIMS"
data = get_company_data(ticker, fast_mode=False)

print(f"Ticker: {data.get('ticker')}")
print(f"Name: {data.get('name')}")
print(f"Trailing EPS (GAAP): {data.get('trailing_eps')}")
print(f"Adjusted EPS (Non-GAAP Anchor): {data.get('adjusted_eps')}")

print("\n--- Analyst Estimates ---")
for est in data.get('eps_estimates', []):
    print(f"{est.get('period')}: {est.get('avg')} (Growth: {est.get('growth')})")

print("\n--- Historical Anchors ---")
for a in data.get('historical_anchors', []):
    print(f"{a.get('year')}: EPS {a.get('eps')}")
