import asyncio
import sys
import os
import json
from api.scraper.yahoo import get_company_data

async def main():
    ticker = 'FDS'
    # get_company_data is synchronous in yahoo.py (though it uses threads)
    data = get_company_data(ticker)
    
    print(f"--- Historical Anchors for {ticker} ---")
    anchors = data.get('historical_anchors', [])
    for a in anchors:
        print(a)
    
    print(f"\n--- Historical Data (for charts) ---")
    hist = data.get('historical_data', {})
    for i in range(len(hist.get('years', []))):
        print(f"Year: {hist['years'][i]}, EPS: {hist['eps'][i]}")

if __name__ == '__main__':
    asyncio.run(main())
