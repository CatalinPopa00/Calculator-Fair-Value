import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        file_path = f"file://{os.getcwd()}/index.html"
        try:
            await page.goto(file_path)

            # Setup dummy values in globalData
            await page.evaluate('''() => {
                window.globalData = {
                    ticker: "AAPL",
                    company_profile: {
                        companyName: "Apple Inc.",
                        mktCap: 3000000000000,
                        industry: "Consumer Electronics"
                    },
                    quote: {
                        price: 150.5
                    },
                    scoring_results: {
                        base: { fair_value: 160 },
                        bear: { fair_value: 120 },
                        bull: { fair_value: 200 }
                    }
                };
                window.customWeights = {
                    dcf: 40,
                    peg: 20,
                    relative: 30,
                    lynch: 10
                };
                // Make sure window._scenarioFvData behaves appropriately for missing values
            }''')

            # Let's mock window._scenarioFvData for this test since it's populated on calculate
            html = await page.evaluate('''() => {
                const formatFv = (val) => val != null ? '$' + val.toFixed(2) : 'N/A';

                // simulate scenarioFvs being missing for unclicked tabs
                const scenarioFvs = window._scenarioFvData || {base: 155.0};

                // if it's missing, try fallback to globalData.scoring_results if available
                const fallbackFvs = (window.globalData && window.globalData.scoring_results) ? window.globalData.scoring_results : {};

                const baseVal = formatFv(scenarioFvs.base ?? fallbackFvs.base?.fair_value);
                const bearVal = formatFv(scenarioFvs.bear ?? fallbackFvs.bear?.fair_value);
                const bullVal = formatFv(scenarioFvs.bull ?? fallbackFvs.bull?.fair_value);

                return { baseVal, bearVal, bullVal };
            }''')
            print("Extracted values:", html)
        except Exception as e:
            print("Error", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
