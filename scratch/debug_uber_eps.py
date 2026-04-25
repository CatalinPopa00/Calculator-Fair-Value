
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scraper.yahoo import get_company_data
import json

ticker = "UBER"
print(f"Fetching data for {ticker}...")
data = get_company_data(ticker)

print("\n--- RESULTS ---")
print(f"Ticker: {data.get('ticker')}")
print(f"Current Price: {data.get('current_price')}")
print(f"Trailing EPS (GAAP): {data.get('trailing_eps')}")
print(f"Adjusted EPS (Non-GAAP): {data.get('adjusted_eps')}")

print("\nHistorical Trends (last 4 years):")
for t in data.get('historical_trends', []):
    print(f"Year {t.get('year')}: EPS={t.get('eps')}, Net Margin={t.get('net_margin')}, GAAP Margin={t.get('gaap_net_margin')}")

print("\nHistorical Anchors:")
print(json.dumps(data.get('historical_anchors', []), indent=2))
