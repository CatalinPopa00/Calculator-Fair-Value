import json
import sys
import os

# Add root to sys.path
sys.path.append(os.getcwd())

from scraper.yahoo import get_analyst_data

ticker = "ADBE"
data = get_analyst_data(ticker)

print(f"--- {ticker} Analyst Data ---")
for est in data.get('eps_estimates', []):
    print(f"Period: {est.get('period')}, Avg: {est.get('avg')}, Status: {est.get('status')}, Growth: {est.get('growth')}")

print(f"Growth Estimate: {data.get('eps_growth')}")
