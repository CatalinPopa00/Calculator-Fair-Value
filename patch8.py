import sys
import re

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
                    if (i === 0 && ests[0].low != null && ests[0].yearAgo != null) {
                        g = (ests[0].low - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                    } else if (i > 0 && ests[i].low != null && ests[i-1].low != null) {
                        g = (ests[i].low - ests[i-1].low) / Math.abs(ests[i-1].low);
                    }
                } else if (_currentScenario === 'bull') {
                    if (i === 0 && ests[0].high != null && ests[0].yearAgo != null) {
                        g = (ests[0].high - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                    } else if (i > 0 && ests[i].high != null && ests[i-1].high != null) {
                        g = (ests[i].high - ests[i-1].high) / Math.abs(ests[i-1].high);
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
                    if (i === 0 && ests[0].low != null && ests[0].yearAgo != null) {
                        g = (ests[0].low - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                    } else if (i > 0 && ests[i].low != null && ests[i-1].low != null) {
                        g = (ests[i].low - ests[i-1].low) / Math.abs(ests[i-1].low);
                    }
                } else if (_currentScenario === 'bull') {
                    if (i === 0 && ests[0].high != null && ests[0].yearAgo != null) {
                        g = (ests[0].high - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                    } else if (i > 0 && ests[i].high != null && ests[i-1].high != null) {
                        g = (ests[i].high - ests[i-1].high) / Math.abs(ests[i-1].high);
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

    # 3. Update Relative Valuation company_eps to only use 'y' periods
    bad_rel_eps = """            let company_eps = (rel.company_fwd_eps || 0) > 0 ? rel.company_fwd_eps : (rel.company_eps || 0);
            
            if (_currentScenario === 'bear' || _currentScenario === 'bull') {
                const eEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported');"""
                
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
            } else if (_currentScenario === 'bear' || _currentScenario === 'bull') {"""

    bad_rel_eps_close = """                    const y2 = _currentScenario === 'bear' ? eEsts[1].low : eEsts[1].high;
                    if (y1 != null && y2 != null) company_eps = (y1 + y2) / 2.0;
                }
            }"""
            
    good_rel_eps_close = """                    const y2 = _currentScenario === 'bear' ? eEsts[1].low : eEsts[1].high;
                    if (y1 != null && y2 != null) company_eps = (y1 + y2) / 2.0;
                }
            }""" # keep the same but we effectively replaced the start. Actually, safer to just replace the whole block.
            
    bad_rel_eps_full = """            let company_eps = (rel.company_fwd_eps || 0) > 0 ? rel.company_fwd_eps : (rel.company_eps || 0);
            
            if (_currentScenario === 'bear' || _currentScenario === 'bull') {
                const eEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported');
                if (eEsts && eEsts.length >= 2) {
                    const y1 = _currentScenario === 'bear' ? eEsts[0].low : eEsts[0].high;
                    const y2 = _currentScenario === 'bear' ? eEsts[1].low : eEsts[1].high;
                    if (y1 != null && y2 != null) company_eps = (y1 + y2) / 2.0;
                }
            }"""
            
    good_rel_eps_full = """            let company_eps = (rel.company_fwd_eps || 0) > 0 ? rel.company_fwd_eps : (rel.company_eps || 0);
            
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
    bad_peg = """            let pegEps = currentFormulaData.peg.eps_estimated || prof.fwd_eps || 0;
            let pegGrowth = currentFormulaData.peg.eps_growth_estimated || prof.earnings_growth || 0.05;"""
            
    good_peg = """            let pegEps = prof.fwd_eps || 0;
            const pegEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported' && e.period && e.period.endsWith('y'));
            if (pegEsts && pegEsts.length >= 2) {
                if (_currentScenario === 'bear') {
                    pegEps = (pegEsts[0].low + pegEsts[1].low) / 2.0;
                } else if (_currentScenario === 'bull') {
                    pegEps = (pegEsts[0].high + pegEsts[1].high) / 2.0;
                } else {
                    pegEps = (pegEsts[0].avg + pegEsts[1].avg) / 2.0;
                }
            } else {
                pegEps = currentFormulaData.peg.eps_estimated || prof.fwd_eps || 0;
            }
            let pegGrowth = getDynamicEpsGrowth();"""

    replacements = [
        (bad_eps_growth, good_eps_growth),
        (bad_eps_loop, good_eps_loop),
        (bad_rev_growth, good_rev_growth),
        (bad_rev_loop, good_rev_loop),
        (bad_rel_eps_full, good_rel_eps_full),
        (bad_peg, good_peg)
    ]

    for b, g in replacements:
        if b in content:
            content = content.replace(b, g)
        else:
            print(f"Failed to find block:\n{b[:100]}...")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success")

if __name__ == '__main__':
    main()
