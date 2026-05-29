import sys

def main():
    file_path = 'c:/Users/Snoozie/Downloads/Calculator-Fair-Value/Calculator-Fair-Value/app.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_eps = """        const getDynamicEpsGrowth = () => {
            const eList = globalData.eps_estimates || [];
            const ests = eList.filter(e => e && e.status !== 'reported');
            let g1 = NaN, g2 = NaN;
            if (ests.length >= 2) {
                if (_currentScenario === 'bear' && ests[0].low != null && ests[0].yearAgo != null && ests[1].low != null) {
                    g1 = (ests[0].low - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                    g2 = (ests[1].low - ests[0].low) / Math.abs(ests[0].low);
                } else if (_currentScenario === 'bull' && ests[0].high != null && ests[0].yearAgo != null && ests[1].high != null) {
                    g1 = (ests[0].high - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                    g2 = (ests[1].high - ests[0].high) / Math.abs(ests[0].high);
                } else {
                    g1 = parseFloat(ests[0].growth);
                    g2 = parseFloat(ests[1].growth);
                }
                if (!isNaN(g1) && !isNaN(g2)) return (g1 + g2) / 2.0;
            } else if (ests.length === 1) {
                if (_currentScenario === 'bear' && ests[0].low != null && ests[0].yearAgo != null) {
                    g1 = (ests[0].low - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                } else if (_currentScenario === 'bull' && ests[0].high != null && ests[0].yearAgo != null) {
                    g1 = (ests[0].high - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                } else {
                    g1 = parseFloat(ests[0].growth);
                }
                if (!isNaN(g1)) return g1;
            }
            return currentFormulaData?.peg?.eps_growth_estimated || globalData?.company_profile?.earnings_growth || 0.05;
        };"""
        
    new_eps = """        const getDynamicEpsGrowth = () => {
            const eList = globalData.eps_estimates || [];
            const ests = eList.filter(e => e && e.status !== 'reported');
            let growths = [];
            for (let i = 0; i < ests.length; i++) {
                let g = NaN;
                if (_currentScenario === 'bear') {
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
        
    old_rev = """        const getDynamicRevGrowth = () => {
            const rList = globalData.rev_estimates || [];
            const ests = rList.filter(e => e && e.status !== 'reported');
            let g1 = NaN, g2 = NaN;
            if (ests.length >= 2) {
                if (_currentScenario === 'bear' && ests[0].low != null && ests[0].yearAgo != null && ests[1].low != null) {
                    g1 = (ests[0].low - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                    g2 = (ests[1].low - ests[0].low) / Math.abs(ests[0].low);
                } else if (_currentScenario === 'bull' && ests[0].high != null && ests[0].yearAgo != null && ests[1].high != null) {
                    g1 = (ests[0].high - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                    g2 = (ests[1].high - ests[0].high) / Math.abs(ests[0].high);
                } else {
                    g1 = parseFloat(ests[0].growth);
                    g2 = parseFloat(ests[1].growth);
                }
                if (!isNaN(g1) && !isNaN(g2)) return (g1 + g2) / 2.0;
            } else if (ests.length === 1) {
                if (_currentScenario === 'bear' && ests[0].low != null && ests[0].yearAgo != null) {
                    g1 = (ests[0].low - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                } else if (_currentScenario === 'bull' && ests[0].high != null && ests[0].yearAgo != null) {
                    g1 = (ests[0].high - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                } else {
                    g1 = parseFloat(ests[0].growth);
                }
                if (!isNaN(g1)) return g1;
            }
            return globalData?.company_profile?.revenue_growth || 0.08;
        };"""

    new_rev = """        const getDynamicRevGrowth = () => {
            const rList = globalData.rev_estimates || [];
            const ests = rList.filter(e => e && e.status !== 'reported');
            let growths = [];
            for (let i = 0; i < ests.length; i++) {
                let g = NaN;
                if (_currentScenario === 'bear') {
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

    if old_eps in content and old_rev in content:
        content = content.replace(old_eps, new_eps)
        content = content.replace(old_rev, new_rev)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Success")
    else:
        print("Failed to find targets")

if __name__ == '__main__':
    main()
