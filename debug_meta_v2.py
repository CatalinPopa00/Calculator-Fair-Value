import asyncio
import sys
import os

# Add api directory to path
sys.path.append(os.path.join(os.getcwd(), 'api'))

from scraper.yahoo import get_company_data

async def debug_meta():
    print("Fetching META data...")
    try:
        data = await get_company_data("META")
        print(f"\nTicker: {data['ticker']}")
        print(f"Historical Years: {data['historical_data']['years']}")
        print(f"Historical EPS: {data['historical_data']['eps']}")
        
        # Check specific years
        for yr, eps in zip(data['historical_data']['years'], data['historical_data']['eps']):
             print(f"Year {yr}: {eps}")
             
    except Exception as e:
        import traceback
        traceback.print_exc()
    
if __name__ == "__main__":
    asyncio.run(debug_meta())
