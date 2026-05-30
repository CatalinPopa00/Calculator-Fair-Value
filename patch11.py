import sys

def main():
    file_path = 'c:/Users/Snoozie/Downloads/Calculator-Fair-Value/Calculator-Fair-Value/app.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update getDynamicEpsGrowth
    bad_eps = """        const getDynamicEpsGrowth = () => {
            const eList = globalData.eps_estimates || [];
            const ests = eList.filter(e => e && e.status !== 'reported');
            let growths = [];
            for (let i = 0; i < ests.length; i++) {
                let g = NaN;
                if (_currentScenario === 'bear') {
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
                } else {
                    g = parseFloat(ests[i].growth);
                }
                if (!isNaN(g)) growths.push(g);
            }
            if (growths.length > 0) {
                const sum = growths.reduce((a, b) => a + b, 0);
                return sum / growths.length;
            }
            return currentFormulaData?.peg?.eps_growth_estimated || globalData?.company_profile?.earnings_growth || 0.05;
        };"""
        
    good_eps = """        const getDynamicEpsGrowth = () => {
            const eList = globalData.eps_estimates || [];
            const annualEsts = eList.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
            
            if (annualEsts.length >= 2) {
                const fy1 = annualEsts[0];
                const fy2 = annualEsts[1];
                let g1 = NaN, g2 = NaN;
                const base1 = fy1.yearAgoEps != null ? fy1.yearAgoEps : fy1.yearAgo;
                
                if (_currentScenario === 'bear') {
                    if (fy1.low != null && base1 != null) g1 = (fy1.low - base1) / Math.abs(base1);
                    if (fy2.low != null && fy1.low != null) g2 = (fy2.low - fy1.low) / Math.abs(fy1.low);
                } else if (_currentScenario === 'bull') {
                    if (fy1.high != null && base1 != null) g1 = (fy1.high - base1) / Math.abs(base1);
                    if (fy2.high != null && fy1.high != null) g2 = (fy2.high - fy1.high) / Math.abs(fy1.high);
                } else {
                    g1 = parseFloat(fy1.growth);
                    g2 = parseFloat(fy2.growth);
                }
                if (!isNaN(g1) && !isNaN(g2)) return (g1 + g2) / 2.0;
                if (!isNaN(g1)) return g1;
            } else if (annualEsts.length === 1) {
                const fy1 = annualEsts[0];
                let g = NaN;
                const base1 = fy1.yearAgoEps != null ? fy1.yearAgoEps : fy1.yearAgo;
                if (_currentScenario === 'bear') {
                    if (fy1.low != null && base1 != null) g = (fy1.low - base1) / Math.abs(base1);
                } else if (_currentScenario === 'bull') {
                    if (fy1.high != null && base1 != null) g = (fy1.high - base1) / Math.abs(base1);
                } else {
                    g = parseFloat(fy1.growth);
                }
                if (!isNaN(g)) return g;
            }
            return currentFormulaData?.peg?.eps_growth_estimated || globalData?.company_profile?.earnings_growth || 0.05;
        };"""

    # 2. Update getDynamicRevGrowth
    bad_rev = """        const getDynamicRevGrowth = () => {
            const rList = globalData.rev_estimates || [];
            const ests = rList.filter(e => e && e.status !== 'reported');
            let growths = [];
            for (let i = 0; i < ests.length; i++) {
                let g = NaN;
                if (_currentScenario === 'bear') {
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
                } else {
                    g = parseFloat(ests[i].growth);
                }
                if (!isNaN(g)) growths.push(g);
            }
            if (growths.length > 0) {
                const sum = growths.reduce((a, b) => a + b, 0);
                return sum / growths.length;
            }
            return globalData?.company_profile?.revenue_growth || 0.08;
        };"""
        
    good_rev = """        const getDynamicRevGrowth = () => {
            const rList = globalData.rev_estimates || [];
            const annualEsts = rList.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
            
            if (annualEsts.length >= 1) {
                const fy1 = annualEsts[0];
                let g = NaN;
                const base = fy1.yearAgoRevenue != null ? fy1.yearAgoRevenue : fy1.yearAgo;
                if (_currentScenario === 'bear') {
                    if (fy1.low != null && base != null) g = (fy1.low - base) / Math.abs(base);
                } else if (_currentScenario === 'bull') {
                    if (fy1.high != null && base != null) g = (fy1.high - base) / Math.abs(base);
                } else {
                    g = parseFloat(fy1.growth);
                }
                if (!isNaN(g)) return g;
            }
            return globalData?.company_profile?.revenue_growth || 0.08;
        };"""

    # 3. Update filters in other places
    bad_filter_peers_eps = "const eEsts = eList.filter(e => e && e.status !== 'reported');"
    good_filter_peers_eps = "const eEsts = eList.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));"

    bad_filter_render_eps = "const eEsts = globalData.eps_estimates.filter(e => e && e.status !== 'reported');"
    good_filter_render_eps = "const eEsts = globalData.eps_estimates.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));"

    bad_filter_render_rev = "const rEsts = globalData.rev_estimates.filter(e => e && e.status !== 'reported');"
    good_filter_render_rev = "const rEsts = globalData.rev_estimates.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));"

    bad_filter_peg = "const pegEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported');"
    good_filter_peg = "const pegEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));"
    
    bad_filter_rel1 = "const eEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported');"
    good_filter_rel1 = "const eEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));"
    
    bad_filter_rel2 = "const rEsts = globalData.rev_estimates?.filter(e => e && e.status !== 'reported');"
    good_filter_rel2 = "const rEsts = globalData.rev_estimates?.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));"


    replacements = [
        (bad_eps, good_eps),
        (bad_rev, good_rev),
    ]

    for b, g in replacements:
        if b in content:
            content = content.replace(b, g)
            print("Successfully replaced a block.")
        else:
            print(f"Failed to find block:\n{b[:100]}...")

    # String replacements for filters
    content = content.replace(bad_filter_peers_eps, good_filter_peers_eps)
    content = content.replace(bad_filter_render_eps, good_filter_render_eps)
    content = content.replace(bad_filter_render_rev, good_filter_render_rev)
    content = content.replace(bad_filter_peg, good_filter_peg)
    content = content.replace(bad_filter_rel1, good_filter_rel1)
    content = content.replace(bad_filter_rel2, good_filter_rel2)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success")

if __name__ == '__main__':
    main()
