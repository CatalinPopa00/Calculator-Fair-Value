import asyncio
import sys
import os
import datetime

# Add api directory to path
sys.path.append(os.path.join(os.getcwd(), 'api'))

from scraper.yahoo import get_company_data

async def diagnose_meta_2025():
    print("--- DIAGNOSING META 2025 ---")
    try:
        data = await get_company_data("META")
        
        # 1. Historical Data check
        years = data['historical_data']['years']
        eps_list = data['historical_data']['eps']
        rev_list = data['historical_data']['revenue']
        
        for y, e, r in zip(years, eps_list, rev_list):
            if y == 2025:
                margin = (e * data['shares_outstanding'] / r) if r > 0 else 0
                print(f"Year {y}: EPS={e}, Rev={r}, Margin={margin:.2%}")
        
        # 2. Check Analyst estimates (center table)
        for e_est in data['eps_estimates']:
            print(f"Estimate Period: {e_est['period']}, Avg: {e_est['avg']}")

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnose_meta_2025())
