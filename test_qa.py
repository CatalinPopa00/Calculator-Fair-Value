import asyncio
from scraper.yahoo import get_company_data

async def main():
    try:
        data = await get_company_data('AAPL')
        print("Success!")
        q_anchors = data.get('quarterly_anchors', [])
        print(f"Got {len(q_anchors)} quarterly anchors.")
        if q_anchors:
            print("First anchor (TTM):", q_anchors[0].get('year'))
            if len(q_anchors) > 1:
                print("Second anchor:", q_anchors[1].get('year'))
                print("Revenue B:", q_anchors[1].get('revenue_b'))
                print("EPS:", q_anchors[1].get('eps'))
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    asyncio.run(main())
