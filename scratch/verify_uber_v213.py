
import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from scraper.yahoo import get_company_data, get_analyst_data

ticker = "UBER"
print(f"--- Verifying {ticker} Final Output (v213) ---")
# Use fast_mode=True to speed up (it still uses the new priority logic)
data = get_company_data(ticker, fast_mode=True)
hist_eps = data.get('historical_data', {}).get('eps', [])
hist_years = data.get('historical_data', {}).get('years', [])

print("\nHistorical EPS (Should be Normalized, not 4.73 for 2025):")
for y, e in zip(hist_years, hist_eps):
    print(f"{y}: {e}")

analyst = get_analyst_data(None, ticker, historical_data=data.get('historical_data'))
print("\nAnalyst Growth Table (v213):")
for e in analyst.get('eps_estimates', []):
    if 'FY' in e['period']:
        print(f"{e['period']}: {e.get('avg')} | Growth: {e.get('growth')}")
