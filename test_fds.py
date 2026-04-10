import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.scraper.yahoo import fetch_financial_data

async def main():
    ticker = 'FDS'
    data = await fetch_financial_data(ticker)
    
    print(f"--- Peers Data for {ticker} ---")
    peers = data.get('peers_data', [])
    for p in peers:
        print(p)
        
    print(f"--- DCF Data for {ticker} ---")
    dcf = data.get('dcf_data', {})
    print(dcf)
    
    print(f"--- Ticker Data ---")
    print(f"Cash: {data.get('cash_and_equivalents')}, Debt: {data.get('total_debt')}")
    print(f"PE: {data.get('pe_ratio')}, EPS Growth Y/Y: {data.get('eps_growth_yoy')}, Revenue Growth Y/Y: {data.get('revenue_growth_yoy')}")

if __name__ == '__main__':
    asyncio.run(main())
