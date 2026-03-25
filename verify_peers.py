
import sys
import os
# Add the current directory to path so we can import api.scraper.yahoo
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_competitors_data

ticker = "MRK"
sector = "Healthcare"
industry = "Drug Manufacturers - General"
market_cap = 290e9

print(f"Fetching peers for {ticker}...")
peers = get_competitors_data(ticker, sector, industry, market_cap)

print(f"\nFound {len(peers)} peers.")
for p in peers[:4]:
    print(f"\nTicker: {p.get('ticker')}")
    print(f"Name: {p.get('name')}")
    print(f"Rev Growth: {p.get('revenue_growth')}")
    print(f"EPS Growth: {p.get('earnings_growth')}")
