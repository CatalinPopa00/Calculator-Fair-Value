
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scraper.yahoo import get_nasdaq_earnings_surprise
import json

ticker = "UBER"
print(f"Fetching Nasdaq surprises for {ticker}...")
rows = get_nasdaq_earnings_surprise(ticker)

print("\n--- NASDAQ SURPRISE ROWS ---")
for row in rows:
    print(row)
