import sys
import os
import json
import math

# Add the project root to sys.path
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value')

from scraper.yahoo import get_company_data

ticker = "META"
print(f"Fetching data for {ticker}...")
data = get_company_data(ticker)

# Emulate api/index.py logic
current_price = data.get("current_price", 0)
eps_for_valuation = data.get("adjusted_eps") or data.get("trailing_eps", 0)
current_pe = current_price / eps_for_valuation if eps_for_valuation > 0 else 0
consensus_growth = data.get("eps_growth")

company_peg = current_pe / (consensus_growth * 100) if consensus_growth > 0 else 0

print(f"Price: {current_price}")
print(f"EPS for Valuation: {eps_for_valuation}")
print(f"Current P/E: {current_pe}")
print(f"Consensus Growth: {consensus_growth}")
print(f"Company PEG: {company_peg}")
print(f"Growth Period: {data.get('eps_growth_period')}")
