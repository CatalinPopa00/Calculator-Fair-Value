// scratch/verify_dcf_model.js
// Verification script for the new Revenue-to-FCF Margin pro-forma projection model

const calcLocalDcf = (fcfObj, growth, wacc, perp, shares, cash, debt, buybackRate = 0, years = 5, exitMult = 10.0, method = 'perpetual') => {
    let fcf = 0;
    let revenue = 0;
    let customMargin = null;
    
    if (fcfObj && typeof fcfObj === 'object') {
        fcf = fcfObj.fcf || 0;
        revenue = fcfObj.revenue || 0;
        customMargin = fcfObj.customMargin;
    } else {
        fcf = fcfObj || 0;
    }

    if (!fcf || !shares || shares <= 0) return null;
    
    const finalWacc = Math.max(0.07, Math.min(wacc, 0.105));
    
    // 1. Determine base Revenue and starting FCF Margin
    let currentRevenue = revenue;
    if (!currentRevenue || currentRevenue <= 0) {
        currentRevenue = fcf / 0.10;
    }
    
    let startingFcfMargin = 0.10;
    if (customMargin !== null && !isNaN(customMargin)) {
        startingFcfMargin = customMargin / 100;
    } else if (currentRevenue > 0) {
        startingFcfMargin = fcf / currentRevenue;
    }
    
    console.log(`[INIT] Base Revenue: $${(currentRevenue / 1e9).toFixed(3)}B`);
    console.log(`[INIT] Base FCF: $${(fcf / 1e9).toFixed(3)}B`);
    console.log(`[INIT] Starting FCF Margin: ${(startingFcfMargin * 100).toFixed(2)}%`);
    
    let pv = 0;
    let currentFcf = fcf;
    const fcf_projections = [];
    const pv_fcf_years = [];
    
    console.log("\n--- Year-by-Year Projections ---");
    for (let i = 1; i <= years; i++) {
        const g = Array.isArray(growth) ? (growth[i - 1] !== undefined ? growth[i - 1] : growth[growth.length - 1]) : growth;
        
        // Revenue grows
        const oldRev = currentRevenue;
        currentRevenue *= (1 + g);
        
        // Margin expansion (+0.2% per year)
        const yearMargin = startingFcfMargin + (i * 0.002);
        
        // FCF
        currentFcf = currentRevenue * yearMargin;
        
        fcf_projections.push(currentFcf);
        
        const pv_fcf = currentFcf / Math.pow(1 + finalWacc, i);
        pv_fcf_years.push(pv_fcf);
        pv += pv_fcf;
        
        console.log(`Year ${i}:`);
        console.log(`  Revenue Growth: ${(g * 100).toFixed(1)}%`);
        console.log(`  Projected Revenue: $${(currentRevenue / 1e9).toFixed(3)}B`);
        console.log(`  FCF Margin (+0.2%): ${(yearMargin * 100).toFixed(2)}%`);
        console.log(`  Projected FCF: $${(currentFcf / 1e9).toFixed(3)}B`);
        console.log(`  Discounted PV: $${(pv_fcf / 1e9).toFixed(3)}B`);
    }
    
    let tv = 0;
    if (method === 'perpetual') {
        tv = (currentFcf * (1 + perp)) / (finalWacc - perp);
    } else {
        tv = currentFcf * exitMult;
    }
    
    const pvTv = tv / Math.pow(1 + finalWacc, years);
    const ev = pv + pvTv;
    const eqVal = ev + (cash || 0) - (debt || 0);
    const effectiveShares = shares * Math.pow(1 - (buybackRate || 0), years);
    const fair_value = eqVal / (effectiveShares > 0 ? effectiveShares : shares);
    
    console.log("\n--- Valuation Summary ---");
    console.log(`Discount Rate (WACC): ${(finalWacc * 100).toFixed(2)}%`);
    console.log(`Sum of PV of Cash Flows: $${(pv / 1e9).toFixed(3)}B`);
    console.log(`Terminal Value (TV): $${(tv / 1e9).toFixed(3)}B`);
    console.log(`PV of Terminal Value: $${(pvTv / 1e9).toFixed(3)}B`);
    console.log(`Enterprise Value (EV): $${(ev / 1e9).toFixed(3)}B`);
    console.log(`Equity Value: $${(eqVal / 1e9).toFixed(3)}B`);
    console.log(`Fair Value Per Share: $${fair_value.toFixed(2)}`);
    
    return fair_value;
};

// ---------------- TEST CASE 1: Automatic FCF Margin (based on last year full) ----------------
console.log("======================================================================");
console.log("TEST CASE 1: AUTOMATIC MARGIN (KO-like scenario)");
console.log("======================================================================");
const fcfParam1 = {
    fcf: 9000000000.0,      // $9B FCF
    revenue: 45000000000.0, // $45B Rev (Starting margin = 20%)
    customMargin: null      // Automatic
};
const growth = [0.08, 0.08, 0.08, 0.06, 0.06, 0.06, 0.04, 0.04, 0.04, 0.04];
const shares = 4300000000;
const cash = 12000000000;
const debt = 38000000000;

calcLocalDcf(fcfParam1, growth, 0.085, 0.025, shares, cash, debt, 0, 10, 15.0, 'perpetual');

// ---------------- TEST CASE 2: Custom FCF Margin Override (e.g. 25%) ----------------
console.log("\n======================================================================");
console.log("TEST CASE 2: CUSTOM MARGIN OVERRIDE (Set to 25%)");
console.log("======================================================================");
const fcfParam2 = {
    fcf: 9000000000.0,      // $9B FCF
    revenue: 45000000000.0, // $45B Rev (Historic = 20%)
    customMargin: 25.0      // Custom starting margin = 25%
};
calcLocalDcf(fcfParam2, growth, 0.085, 0.025, shares, cash, debt, 0, 10, 15.0, 'perpetual');
