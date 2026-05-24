const puppeteer = require('puppeteer');
const wait = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
    page.on('pageerror', err => console.log('BROWSER ERROR:', err.toString()));

    try {
        await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle2' });
        await wait(2000);
        console.log("Searching for AAPL...");
        await page.type('#ticker-input', 'AAPL');
        await page.click('#search-btn');
        await page.waitForSelector('#dcf-value', { visible: true, timeout: 60000 });
        await wait(2000);
        
        const models = ['dcf', 'relative', 'graham', 'peg', 'piotroski'];
        
        for (const model of models) {
            console.log(`Testing View Data for ${model}...`);
            const btn = await page.$(`button.view-data-btn[data-method="${model}"]`);
            if (btn) {
                await page.click(`button.view-data-btn[data-method="${model}"]`);
                await wait(1000);
                
                const isModalVisible = await page.evaluate(() => {
                    const modal = document.getElementById('data-modal');
                    return modal && window.getComputedStyle(modal).display !== 'none';
                });
                console.log(`Modal visible for ${model}: ${isModalVisible}`);
                
                if (isModalVisible) {
                    await page.evaluate(() => {
                        const modal = document.getElementById('data-modal');
                        modal.style.display = 'none'; // close it for the next one
                    });
                } else {
                    console.error(`View data failed for ${model}!`);
                }
            } else {
                console.error(`Button for ${model} not found!`);
            }
        }
    } catch (e) {
        console.error("Test failed:", e);
    } finally {
        await browser.close();
    }
})();
