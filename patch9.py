import sys

def main():
    file_path = 'c:/Users/Snoozie/Downloads/Calculator-Fair-Value/Calculator-Fair-Value/app.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update getDynamicEpsGrowth
    bad_eps_growth = """        const getDynamicEpsGrowth = () => {
            const eList = globalData.eps_estimates || [];
            const ests = eList.filter(e => e && e.status !== 'reported');"""
    good_eps_growth = """        const getDynamicEpsGrowth = () => {
            const eList = globalData.eps_estimates || [];
            const ests = eList.filter(e => e && e.status !== 'reported' && e.period && e.period.endsWith('y'));"""

    # Fix the yearAgo vs yearAgoEps logic in getDynamicEpsGrowth
    bad_eps_loop = """                if (_currentScenario === 'bear') {
                    if (ests[i].low != null && ests[i].yearAgoEps != null) {
                        g = (ests[i].low - ests[i].yearAgoEps) / Math.abs(ests[i].yearAgoEps);
                    } else if (ests[i].low != null && ests[i].yearAgo != null) {
                        g = (ests[i].low - ests[i].yearAgo) / Math.abs(ests[i].yearAgo);
                    }
                } else if (_currentScenario === 'bull') {
                    if (ests[i].high != null && ests[i].yearAgoEps != null) {
                        g = (ests[i].high - ests[i].yearAgoEps) / Math.abs(ests[i].yearAgoEps);
                    } else if (ests[i].high != null && ests[i].yearAgo != null) {
                        g = (ests[i].high - ests[i].yearAgo) / Math.abs(ests[i].yearAgo);
                    }
                } else {"""
    good_eps_loop = """                if (_currentScenario === 'bear') {
                    if (ests[i].low != null && ests[i].yearAgoEps != null) {
                        g = (ests[i].low - ests[i].yearAgoEps) / Math.abs(ests[i].yearAgoEps);
                    } else if (ests[i].low != null && ests[i].yearAgo != null) {
                        g = (ests[i].low - ests[i].yearAgo) / Math.abs(ests[i].yearAgo);
                    }
                } else if (_currentScenario === 'bull') {
                    if (ests[i].high != null && ests[i].yearAgoEps != null) {
                        g = (ests[i].high - ests[i].yearAgoEps) / Math.abs(ests[i].yearAgoEps);
                    } else if (ests[i].high != null && ests[i].yearAgo != null) {
                        g = (ests[i].high - ests[i].yearAgo) / Math.abs(ests[i].yearAgo);
                    }
                } else {"""
                
    # 2. Update getDynamicRevGrowth
    bad_rev_growth = """        const getDynamicRevGrowth = () => {
            const rList = globalData.rev_estimates || [];
            const ests = rList.filter(e => e && e.status !== 'reported');"""
    good_rev_growth = """        const getDynamicRevGrowth = () => {
            const rList = globalData.rev_estimates || [];
            const ests = rList.filter(e => e && e.status !== 'reported' && e.period && e.period.endsWith('y'));"""

    bad_rev_loop = """                if (_currentScenario === 'bear') {
                    if (ests[i].low != null && ests[i].yearAgoEps != null) {
                        g = (ests[i].low - ests[i].yearAgoEps) / Math.abs(ests[i].yearAgoEps);
                    } else if (ests[i].low != null && ests[i].yearAgo != null) {
                        g = (ests[i].low - ests[i].yearAgo) / Math.abs(ests[i].yearAgo);
                    }
                } else if (_currentScenario === 'bull') {
                    if (ests[i].high != null && ests[i].yearAgoEps != null) {
                        g = (ests[i].high - ests[i].yearAgoEps) / Math.abs(ests[i].yearAgoEps);
                    } else if (ests[i].high != null && ests[i].yearAgo != null) {
                        g = (ests[i].high - ests[i].yearAgo) / Math.abs(ests[i].yearAgo);
                    }
                } else {"""
    good_rev_loop = """                if (_currentScenario === 'bear') {
                    if (ests[i].low != null && ests[i].yearAgoRevenue != null) {
                        g = (ests[i].low - ests[i].yearAgoRevenue) / Math.abs(ests[i].yearAgoRevenue);
                    } else if (ests[i].low != null && ests[i].yearAgo != null) {
                        g = (ests[i].low - ests[i].yearAgo) / Math.abs(ests[i].yearAgo);
                    }
                } else if (_currentScenario === 'bull') {
                    if (ests[i].high != null && ests[i].yearAgoRevenue != null) {
                        g = (ests[i].high - ests[i].yearAgoRevenue) / Math.abs(ests[i].yearAgoRevenue);
                    } else if (ests[i].high != null && ests[i].yearAgo != null) {
                        g = (ests[i].high - ests[i].yearAgo) / Math.abs(ests[i].yearAgo);
                    }
                } else {"""

    # 3. Update Relative Valuation company_eps
    bad_rel_eps = """            let company_eps = (rel.company_fwd_eps || 0) > 0 ? rel.company_fwd_eps : (rel.company_eps || 0);
            
            if (_currentScenario === 'bear' || _currentScenario === 'bull') {
                const eEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported');
                if (eEsts && eEsts.length >= 2) {
                    const y1 = _currentScenario === 'bear' ? eEsts[0].low : eEsts[0].high;
                    const y2 = _currentScenario === 'bear' ? eEsts[1].low : eEsts[1].high;
                    if (y1 != null && y2 != null) company_eps = (y1 + y2) / 2.0;
                }
            }"""
            
    good_rel_eps = """            let company_eps = (rel.company_fwd_eps || 0) > 0 ? rel.company_fwd_eps : (rel.company_eps || 0);
            
            const eEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported' && e.period && e.period.endsWith('y'));
            if (eEsts && eEsts.length >= 2) {
                if (_currentScenario === 'bear') {
                    company_eps = (eEsts[0].low + eEsts[1].low) / 2.0;
                } else if (_currentScenario === 'bull') {
                    company_eps = (eEsts[0].high + eEsts[1].high) / 2.0;
                } else {
                    company_eps = (eEsts[0].avg + eEsts[1].avg) / 2.0;
                }
            }"""

    # 4. Update PEG Valuation
    bad_peg = """            const eps = globalData.company_profile.adjusted_eps || globalData.company_profile.trailing_eps || 0;
            // v299: Use _realApiPrice for valuation anchor to prevent Fair Value drift during simulation
            const currentPe = (eps > 0) ? (_realApiPrice / eps) : (currentFormulaData.peg.current_pe || (parseFloat(globalData.company_profile.current_pe) || parseFloat(globalData.company_profile.trailing_pe) || 0));"""
            
    good_peg = """            let eps = globalData.company_profile.adjusted_eps || globalData.company_profile.trailing_eps || 0;
            const pegEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported' && e.period && e.period.endsWith('y'));
            if (pegEsts && pegEsts.length >= 2) {
                if (_currentScenario === 'bear') {
                    eps = (pegEsts[0].low + pegEsts[1].low) / 2.0;
                } else if (_currentScenario === 'bull') {
                    eps = (pegEsts[0].high + pegEsts[1].high) / 2.0;
                } else {
                    eps = (pegEsts[0].avg + pegEsts[1].avg) / 2.0;
                }
            }
            // v299: Use _realApiPrice for valuation anchor to prevent Fair Value drift during simulation
            const currentPe = (eps > 0) ? (_realApiPrice / eps) : (currentFormulaData.peg.current_pe || (parseFloat(globalData.company_profile.current_pe) || parseFloat(globalData.company_profile.trailing_pe) || 0));"""

    replacements = [
        (bad_eps_growth, good_eps_growth),
        (bad_eps_loop, good_eps_loop),
        (bad_rev_growth, good_rev_growth),
        (bad_rev_loop, good_rev_loop),
        (bad_rel_eps, good_rel_eps),
        (bad_peg, good_peg)
    ]

    for b, g in replacements:
        if b in content:
            content = content.replace(b, g)
            print("Successfully replaced a block.")
        else:
            print(f"Failed to find block:\n{b[:100]}...")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success")

if __name__ == '__main__':
    main()
