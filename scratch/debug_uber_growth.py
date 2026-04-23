
import os
import sys
project_root = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value"
sys.path.append(project_root)

from scraper.yahoo import get_company_data
import json

d = get_company_data('UBER')
trends = d.get("historical_trends", [])
g0 = trends[-2].get("eps_growth") if len(trends) >= 2 else "N/A"
g1 = trends[-1].get("eps_growth") if len(trends) >= 1 else "N/A"
final = d.get("eps_growth")

print(f"Ticker: UBER")
print(f"Trend Year 2026 Growth: {g0}")
print(f"Trend Year 2027 Growth: {g1}")
print(f"Final EPS Growth (v223): {final}")
print(f"Label: {d.get('eps_growth_period')}")
