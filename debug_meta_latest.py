import asyncio
import sys
import os

# Add api directory to path
sys.path.append(os.path.join(os.getcwd(), 'api'))

from scraper.yahoo import get_company_data

async def debug_meta():
    print("Fetching META data...")
    data = await get_company_data("META")
    
    print(f"\nTicker: {data['ticker']}")
    print(f"Current Price: {data['current_price']}")
    
    print("\nHistorical EPS Anchors:")
    for h in data['historical_anchors']:
        print(f"Year: {h['year']}, EPS: {h['eps']}")
    
    print(f"\nTrailing EPS (from info/scraper): {data['trailing_eps']}")
    print(f"Adjusted EPS (Non-GAAP): {data.get('adjusted_eps')}")
    
if __name__ == "__main__":
    asyncio.run(debug_meta())
