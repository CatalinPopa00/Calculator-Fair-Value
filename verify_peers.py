import sys
import os

# Add the current directory to sys.path to import local modules
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_competitors_data

def test_peer_filtering():
    print("--- Testing Peer Filtering Logic (GOOG vs GOOGL) ---")
    
    # Simulate a search for GOOG
    target_ticker = "GOOG"
    sector = "Communication Services"
    industry = "Internet Content & Information"
    
    peers = get_competitors_data(target_ticker, sector, industry, limit=5)
    
    print(f"\nTarget: {target_ticker}")
    print(f"Peers returned: {[p['ticker'] for p in peers]}")
    
    googl_present = any(p['ticker'] == 'GOOGL' for p in peers)
    if googl_present:
        print("❌ FAILED: GOOGL should not be a peer for GOOG.")
    else:
        print("✅ PASSED: GOOGL was successfully filtered out.")

    print("\n--- End of Test ---")

if __name__ == "__main__":
    test_peer_filtering()
