const fs = require('fs');
let code = fs.readFileSync('app.js', 'utf8');

const animateFuncTarget = `// --- PRICE ANIMATION UTILITY ---
const animatePriceUI = (oldPrice, newPrice) => {
    if (!oldPrice || oldPrice === newPrice) return;`;

const animateFuncReplacement = `// --- PRICE ANIMATION UTILITY ---
const animatePriceUI = (openPrice, newPrice, triggerFlash = true) => {
    if (!openPrice || openPrice === newPrice) {
        const ti = document.getElementById('price-trend-icon');
        if (ti) ti.textContent = '';
        const sti = document.getElementById('sticky-price-trend-icon');
        if (sti) sti.textContent = '';
        return;
    }`;

code = code.replace(animateFuncTarget, animateFuncReplacement);

const animateFuncBodyTarget = `    const isUp = newPrice > oldPrice;
    const color = isUp ? '#10b981' : '#ef4444';
    const icon = isUp ? '▲' : '▼';
    const pulseClass = isUp ? 'price-flash-green' : 'price-flash-red';

    if (trendIcon && !_simulating) {
        trendIcon.textContent = icon;
        trendIcon.style.color = color;
    }
    if (stickyTrendIcon && !_simulating) {
        stickyTrendIcon.textContent = icon;
        stickyTrendIcon.style.color = color;
    }

    if (priceEl && !_simulating) {`;

const animateFuncBodyReplacement = `    const isUp = newPrice > openPrice;
    const color = isUp ? '#10b981' : '#ef4444';
    const icon = isUp ? '▲' : '▼';
    const pulseClass = isUp ? 'price-flash-green' : 'price-flash-red';

    if (trendIcon && !_simulating) {
        trendIcon.textContent = icon;
        trendIcon.style.color = color;
    }
    if (stickyTrendIcon && !_simulating) {
        stickyTrendIcon.textContent = icon;
        stickyTrendIcon.style.color = color;
    }

    if (triggerFlash && priceEl && !_simulating) {`;

code = code.replace(animateFuncBodyTarget, animateFuncBodyReplacement);

const recalcTarget = `        if (!_simulating && prevPrice !== null && simPrice !== prevPrice) {
             animatePriceUI(prevPrice, simPrice);
        } else if (_simulating) {`;

const recalcReplacement = `        if (!_simulating && globalData && globalData.company_profile && globalData.company_profile.open_price) {
             const openPrice = globalData.company_profile.open_price;
             const priceChanged = prevPrice !== null && simPrice !== prevPrice;
             animatePriceUI(openPrice, simPrice, priceChanged);
        } else if (_simulating) {`;

code = code.replace(recalcTarget, recalcReplacement);

const initialLoadTarget = `        elements.currentPrice.textContent = formatCurrency(data.current_price);`;

const initialLoadReplacement = `        elements.currentPrice.textContent = formatCurrency(data.current_price);
        if (data.company_profile && data.company_profile.open_price) {
            animatePriceUI(data.company_profile.open_price, data.current_price, false);
        }`;

code = code.replace(initialLoadTarget, initialLoadReplacement);


// Also update live polling block
const livePollTarget = `                    // Re-calculate everything with the new price
                    if (typeof recalcWithSimPrice === 'function') {
                        recalcWithSimPrice(data.price, true);
                    }`;

const livePollReplacement = `                    // Update open_price if provided
                    if (data.open_price && globalData.company_profile) {
                        globalData.company_profile.open_price = data.open_price;
                    }

                    // Re-calculate everything with the new price
                    if (typeof recalcWithSimPrice === 'function') {
                        recalcWithSimPrice(data.price, true);
                    }`;

code = code.replace(livePollTarget, livePollReplacement);

fs.writeFileSync('app.js', code);
