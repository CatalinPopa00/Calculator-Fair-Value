import sys
import os
import json

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.yahoo import get_competitors_data

def debug_peers():
    peers = get_competitors_data('NOW', limit=10)
    for p in peers:
        print(f"Ticker: {p.get('ticker')}")
        print(f"  pe_ratio: {p.get('pe_ratio')}")
        print(f"  forward_eps: {p.get('forward_eps')}")
        print(f"  price: {p.get('price')}")
        print(f"  ev_to_ebitda: {p.get('ev_to_ebitda')}")
        print(f"  forward_ebitda: {p.get('forward_ebitda')}")
        print("---")

if __name__ == "__main__":
    debug_peers()
