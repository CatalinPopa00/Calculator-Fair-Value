import os
import sys

# Add the current directory to sys.path so we can import from 'api'
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_competitors_data, get_company_data

ticker = "CRDO"
print(f"--- Fetching data for {ticker} ---")
data = get_company_data(ticker)
if data:
    sector = data.get('sector')
    industry = data.get('industry')
    print(f"Sector: {sector}")
    print(f"Industry: {industry}")
    
    peers = get_competitors_data(ticker, sector, industry)
    print(f"\n--- Peers Found ({len(peers)}) ---")
    for p in peers:
        print(f"- {p['ticker']}: {p['name']} (Price: {p.get('price')}, PE: {p.get('pe_ratio')})")
else:
    print("FAILED to fetch basic company data.")
