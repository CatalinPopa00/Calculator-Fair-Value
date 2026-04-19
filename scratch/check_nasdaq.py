import sys
import os

# Add api directory to path
sys.path.append(os.path.abspath("api"))

from scraper.yahoo import get_nasdaq_historical_eps

res = get_nasdaq_historical_eps("ADBE")
print(f"Results: {len(res)}")
for r in res[:5]:
    print(r)
