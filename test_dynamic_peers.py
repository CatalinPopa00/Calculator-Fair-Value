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
    
    sector = data.get("sector")
    industry = data.get("industry")
    market_cap = data.get("market_cap") or 0.0
    
    # This should trigger Yahoo recommendations fallback if Finnhub is empty/dots-only
    peers = get_competitors_data(ticker, sector, industry, market_cap)
    
    print(f"Peers found: {[p['ticker'] for p in peers]}")
    
    for p in peers:
        print(f"Peer {p['ticker']}:")
        print(f"  Market Cap: {p.get('market_cap')}")
        print(f"  PE: {p.get('pe_ratio')}")
        print(f"  EPS: {p.get('eps')}")
        print(f"  Margin: {p.get('margin')}")
        if '.' in p['ticker']:
            print(f"  WARNING: Ticker {p['ticker']} contains a dot!")

if __name__ == "__main__":
    # NVO is the main test case for dynamic fallback
    test_ticker("NVO")
    
    # TSM usually has dots in its competitors (e.g. 2330.TW)
    test_ticker("TSM")
    
    # AAPL for standard comparison
    test_ticker("AAPL")
