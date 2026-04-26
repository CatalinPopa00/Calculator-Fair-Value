import sys
import os
import json

# Add the project root to sys.path
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value')

from scraper.yahoo import get_company_data

ticker = "ABNB"
print(f"Fetching data for {ticker}...")
data = get_company_data(ticker)

# Print key metrics
print(f"Price: {data.get('current_price')}")
print(f"Trailing EPS: {data.get('trailing_eps')}")
print(f"Adjusted EPS: {data.get('adjusted_eps')}")
print(f"EPS Growth: {data.get('eps_growth')}")
print(f"Current Ratio: {data.get('current_ratio')}")
print(f"Shares: {data.get('shares_outstanding')}")

# Check for anomalies in trend
print("\nProjections:")
for t in data.get('historical_trends', []):
    if "Est" in str(t.get("year", "")):
        print(f"Year: {t.get('year')}, EPS: {t.get('eps')}, Growth: {t.get('eps_growth')}")
