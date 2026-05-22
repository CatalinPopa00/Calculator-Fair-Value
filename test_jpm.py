import asyncio
from scraper.yahoo import get_company_data

async def check_jpm():
    data = get_company_data("JPM")
    print(f"CET1 Ratio: {data.get('cet1_ratio')}")
    print(f"Historic BVPS Growth: {data.get('historic_bvps_growth')}")
    print(f"ROA: {data.get('roa')}")

if __name__ == "__main__":
    asyncio.run(check_jpm())
