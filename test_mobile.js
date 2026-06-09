const { chromium, devices } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    ...devices['iPhone 12']
  });
  const page = await context.newPage();
  await page.goto('file://' + process.cwd() + '/index.html');

  await page.evaluate(() => {
    document.getElementById('company-ticker').textContent = 'BRK-B';
    document.getElementById('company-name').textContent = 'Berkshire Hathaway Inc. New';
    document.getElementById('current-price').textContent = '$487.00';
    document.getElementById('price-trend-icon').textContent = '▲';
    document.getElementById('dashboard').style.display = 'block';
  });

  await page.screenshot({ path: 'mobile.png', fullPage: true });

  await browser.close();
})();
