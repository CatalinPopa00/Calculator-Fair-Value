const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Navigate to the local server
  await page.goto('http://127.0.0.1:8000');

  // Wait for the app to load
  await page.waitForTimeout(1000);

  // Evaluate script to inject Rule 40 data and update UI
  await page.evaluate(() => {
    // Mock the global state
    window.stockData = {
        rule_40: {
            fwd_revenue_growth: 14.5,
            fcf_margin: 42.2,
            score: 56.7
        }
    };

    // Call the update function
    if (typeof updateRule40UI === 'function') {
        updateRule40UI(window.stockData.rule_40);
    }
  });

  // Wait for UI to update
  await page.waitForTimeout(500);

  // Take screenshot of the main dashboard Rule 40 element
  const rule40Element = await page.locator('#rule40-score-row');
  if (await rule40Element.count() > 0) {
      await rule40Element.first().screenshot({ path: 'rule40_dashboard_element.png' });
      console.log('Saved rule40_dashboard_element.png');
  } else {
      console.log('Rule of 40 element not found on dashboard');
  }

  await browser.close();
})();
