from scraper.yahoo import get_competitors_data
import logging
logging.basicConfig(level=logging.DEBUG)
print("=== With cache ===")
peers = get_competitors_data('FISV', limit=10)
print(f"Len peers: {len(peers)}")

print("=== With force_refresh=True ===")
peers = get_competitors_data('FISV', limit=10, force_refresh=True)
print(f"Len peers: {len(peers)}")
