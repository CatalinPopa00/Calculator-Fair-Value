import os
import sys

# Add the current directory to sys.path to import from api
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_company_data, get_competitors_data

def test_ticker(ticker):
    print(f"\n--- Testing Dynamic Peers for {ticker} ---")
    data = get_company_data(ticker)
    if not data:
        print(f"Failed to get data for {ticker}")
        return
    
    print(f"Name: {data['name']}")
    print(f"Sector: {data.get('sector')}")
    print(f"Industry: {data.get('industry')}")
    
    sector = data.get("sector")
    industry = data.get("industry")
    market_cap = data.get("market_cap") or 0.0
    
    peers = get_competitors_data(ticker, sector, industry, market_cap)
    
    print(f"Peers matching sector/industry: {[p['ticker'] for p in peers]}")
    
    for p in peers:
        print(f"Peer {p['ticker']}:")
        print(f"  Sector: {p.get('sector')}")
        print(f"  Industry: {p.get('industry')}")
        if sector and p.get('sector') != sector:
            print(f"  WARNING: Sector mismatch! {p.get('sector')} != {sector}")
        if '.' in p['ticker']:
            print(f"  WARNING: Ticker {p['ticker']} contains a dot!")

if __name__ == "__main__":
    # NVO is the main test case for dynamic fallback
    test_ticker("NVO")
    
    # TSM usually has dots in its competitors (e.g. 2330.TW)
    test_ticker("TSM")
    
    # AAPL for standard comparison
    test_ticker("AAPL")
