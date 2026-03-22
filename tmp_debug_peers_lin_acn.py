import sys
import os
import yfinance as yf

# Sync path
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_competitors_data

def debug_peers(ticker):
    print(f"\n--- Debugging Peers for {ticker} ---")
    stock = yf.Ticker(ticker)
    info = stock.info
    sector = info.get('sector')
    industry = info.get('industry')
    print(f"Sector: {sector}")
    print(f"Industry: {industry}")
    
    peers = get_competitors_data(ticker, sector, industry, limit=5)
    print(f"Found {len(peers)} peers:")
    for p in peers:
        print(f" - {p.get('ticker')}: {p.get('name')} ({p.get('industry')})")

if __name__ == "__main__":
    debug_peers("LIN")
    debug_peers("ACN")
