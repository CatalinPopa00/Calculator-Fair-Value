const fs = require('fs');

const prof = {
    revenue_growth: 0.1,
    earnings_growth: 0.1,
    fwd_pe: 11.0,
    forward_pe: 11.0,
    fwd_ps: 4.0,
    forward_ev_sales: 4.0,
    market_cap: 250000000000,
    shares_outstanding: 500000000,
};

const _realApiPrice = 259.21;
let _currentScenario = 'bear';

const globalData = {
    company_profile: prof,
    eps_estimates: [
        { period: "FY 2025", avg: 20.94, status: "reported" },
        { period: "FY 2026", avg: 23.55, low: 23.27, high: 24.78, status: "estimate" },
        { period: "FY 2027", avg: 26.38, low: 24.07, high: 28.52, status: "estimate" }
    ],
    rev_estimates: [
        { period: "FY 2025", avg: 23.76, status: "reported" },
        { period: "FY 2026", avg: 26.09, low: 25.79, high: 27.33, status: "estimate" },
        { period: "FY 2027", avg: 28.43, low: 27.02, high: 31.43, status: "estimate" }
    ]
};

function runSimulation(scenario) {
    _currentScenario = scenario;
    
    // Line 2524
    const company_shares = prof.shares_outstanding;
    let rel = {};
    let company_eps = 0;
    let company_sales_share = 0;
    
    // Line 2529
    const eEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
    if (eEsts && eEsts.length >= 2) {
        if (_currentScenario === 'bear') company_eps = (eEsts[0].low + eEsts[1].low) / 2.0;
        else if (_currentScenario === 'bull') company_eps = (eEsts[0].high + eEsts[1].high) / 2.0;
        else company_eps = (eEsts[0].avg + eEsts[1].avg) / 2.0;
    }
    
    // Line 2540
    const rEsts = globalData.rev_estimates?.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
    if (rEsts && rEsts.length >= 2) {
        let avgRev;
        if (_currentScenario === 'bear') avgRev = (rEsts[0].low + rEsts[1].low) / 2.0;
        else if (_currentScenario === 'bull') avgRev = (rEsts[0].high + rEsts[1].high) / 2.0;
        else avgRev = (rEsts[0].avg + rEsts[1].avg) / 2.0;
        
        if (avgRev != null && company_shares > 0) company_sales_share = avgRev / company_shares;
    }
    
    rel.dynamic_company_eps = company_eps;
    rel.dynamic_company_sales_share = company_sales_share;
    
    let dynEpsG = prof.earnings_growth;
    let dynRevG = prof.revenue_growth;
    
    rel.dynamic_eps_growth = dynEpsG;
    rel.dynamic_rev_growth = dynRevG;
    
    const r = rel;
    
    // Line 5480
    const impliedPe = r.dynamic_company_eps > 0 ? (_realApiPrice / r.dynamic_company_eps) : (prof.fwd_pe);
    const rev = r.dynamic_company_sales_share ? r.dynamic_company_sales_share * company_shares : 0;
    const impliedPs = rev > 0 ? (prof.market_cap / rev) : null;
    
    console.log(`[${scenario}] company_eps=${company_eps.toFixed(2)}, impliedPe=${impliedPe.toFixed(2)}, impliedPs=${impliedPs ? impliedPs.toFixed(2) : null}`);
}

runSimulation('bear');
runSimulation('base');
runSimulation('bull');
