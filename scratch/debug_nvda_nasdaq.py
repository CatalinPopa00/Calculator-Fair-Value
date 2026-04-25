
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scraper.yahoo import get_nasdaq_earnings_surprise
import json

ticker = "NVDA"
print(f"Fetching Nasdaq surprises for {ticker}...")
rows = get_nasdaq_earnings_surprise(ticker)

print(f"\n--- NASDAQ SURPRISE ROWS ({len(rows)}) ---")
for row in rows[:8]:
    print(row)
