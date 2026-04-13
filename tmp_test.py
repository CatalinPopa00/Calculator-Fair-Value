import sys
from api.scraper.yahoo import get_competitors_data

def test_ticker(ticker, sector, industry):
    print(f"\nTesting {ticker} ({sector} - {industry})")
    peers = get_competitors_data(ticker, sector, industry, limit=5)
    for p in peers:
        print(f"  - {p.get('ticker')}: {p.get('sector')} - {p.get('industry')}")

if __name__ == "__main__":
    test_ticker('PLTR', 'Technology', 'Software—Infrastructure')
    test_ticker('TSLA', 'Consumer Cyclical', 'Auto Manufacturers')
    test_ticker('ADBE', 'Technology', 'Software—Infrastructure')
