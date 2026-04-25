
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scraper.yahoo import get_company_data
import json

ticker = "UBER"
data = get_company_data(ticker)

print(f"Ticker: {data.get('ticker')}")
print(f"FWD PE: {data.get('fwd_pe')}")
print(f"Trailing PE: {data.get('company_profile', {}).get('trailing_pe')}")

print("\nEPS Estimates:")
for e in data.get('eps_estimates', []):
    print(f"{e.get('period')}: {e.get('avg')} (Growth: {e.get('growth')})")
