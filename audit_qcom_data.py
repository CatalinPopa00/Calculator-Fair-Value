import sys
import os
import json
from datetime import datetime

# Add root and api to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'api'))

from api.scraper.yahoo import (
    get_company_data, 
    get_analyst_data, 
    get_nasdaq_comprehensive_estimates,
    get_period_labels
)
import yfinance as yf

ticker = "QCOM"
print(f"--- QCOM Comprehensive Audit ---")

# Step 1: Get full company data
data = get_company_data(ticker)
print(f"Company Name: {data.get('name')}")
print(f"Trailing EPS (GAAP): {data.get('trailing_eps')}")
print(f"Adjusted EPS (Non-GAAP): {data.get('adjusted_eps')}")

# Step 2: Check Historical Anchors
anchors = data.get('historical_anchors', [])
print("\n--- Historical Anchors ---")
for a in anchors:
    print(f"Year {a.get('year')}: EPS {a.get('eps')}")

# Step 3: Check Analyst Estimates
analyst = get_analyst_data(ticker)
eps_est = analyst.get('eps_estimates', [])
print("\n--- Analyst EPS Estimates ---")
for e in eps_est:
    print(f"Period: {e.get('period')}, Avg: {e.get('avg')}, Growth: {e.get('growth')}, Status: {e.get('status')}")

# Step 4: Trace Growth Calculation
# If FY 2026 growth is 121.2%, what was the baseline?
fy0 = next((e for e in eps_est if "FY 2026" in e['period']), None)
if fy0 and fy0.get('growth'):
    baseline = fy0['avg'] / (1 + fy0['growth'])
    print(f"\nCalculated Baseline for FY 2026: {baseline}")
