const fs = require('fs');

async function test() {
    // 1. Fetch data directly from python wrapper script
    const { execSync } = require('child_process');
    const pyOutput = execSync('python -c "import json; from scraper.yahoo import get_company_data; print(json.dumps(get_company_data(\'ADBE\')))"').toString();
    const globalData = JSON.parse(pyOutput);
    
    // 2. Extract values
    const eEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
    const rEsts = globalData.rev_estimates?.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
    
    let bearEps = 0, baseEps = 0, bullEps = 0;
    if (eEsts && eEsts.length >= 2) {
        bearEps = (eEsts[0].low + eEsts[1].low) / 2.0;
        bullEps = (eEsts[0].high + eEsts[1].high) / 2.0;
        baseEps = (eEsts[0].avg + eEsts[1].avg) / 2.0;
    }
    
    const price = globalData.current_price;
    console.log({
        eEsts,
        bearEps,
        baseEps,
        bullEps,
        bearPE: price / bearEps,
        basePE: price / baseEps,
        bullPE: price / bullEps,
        fwdPE: globalData.fwd_pe,
        forwardPE: globalData.forward_pe,
        company_profile_fwd_pe: globalData.company_profile?.fwd_pe
    });
}

test();
