
import sys
import os
import json

# Simulate environment of api/index.py
current_dir = r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\api'
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.dirname(current_dir))

from scraper.yahoo import get_company_data, get_analyst_data

ticker = 'AAPL'
print(f"--- API Environment Diagnostic for {ticker} ---")
cd = get_company_data(ticker, fast_mode=True)
hist_data = cd.get('historical_data')
print("Historical Data Years:", hist_data['years'])
print("Historical Data EPS:", hist_data['eps'])

result = get_analyst_data(ticker, historical_data=hist_data)
for e in result.get('eps_estimates', []):
    if 'FY' in e['period']:
        print(f"Period: {e['period']}, Avg: {e.get('avg')}, Growth: {e.get('growth')}")
