const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto('file://' + process.cwd() + '/index.html');

  // mock some data
  await page.evaluate(() => {
    document.getElementById('company-ticker').textContent = 'BRK-B';
    document.getElementById('company-name').textContent = 'Berkshire Hathaway Inc. New';
    document.getElementById('current-price').textContent = '$487.00';
    document.getElementById('price-trend-icon').textContent = '▲';
    document.getElementById('dashboard').style.display = 'block';
  });

  // set viewport to desktop
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.screenshot({ path: 'desktop.png', fullPage: true });

  await browser.close();
})();
