import sys

def main():
    file_path = 'c:/Users/Snoozie/Downloads/Calculator-Fair-Value/Calculator-Fair-Value/app.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    bad_rev = """        const getDynamicRevGrowth = () => {
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
        
    good_rev = """        const getDynamicRevGrowth = () => {
            const rList = globalData.rev_estimates || [];
            const annualEsts = rList.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
            
            if (annualEsts.length >= 2) {
                const fy1 = annualEsts[0];
                const fy2 = annualEsts[1];
                let g1 = NaN, g2 = NaN;
                const base1 = fy1.yearAgoRevenue != null ? fy1.yearAgoRevenue : fy1.yearAgo;
                
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
                const base1 = fy1.yearAgoRevenue != null ? fy1.yearAgoRevenue : fy1.yearAgo;
                if (_currentScenario === 'bear') {
                    if (fy1.low != null && base1 != null) g = (fy1.low - base1) / Math.abs(base1);
                } else if (_currentScenario === 'bull') {
                    if (fy1.high != null && base1 != null) g = (fy1.high - base1) / Math.abs(base1);
                } else {
                    g = parseFloat(fy1.growth);
                }
                if (!isNaN(g)) return g;
            }
            return globalData?.company_profile?.revenue_growth || 0.08;
        };"""

    if bad_rev in content:
        content = content.replace(bad_rev, good_rev)
        print("Successfully replaced getDynamicRevGrowth.")
    else:
        print("Failed to find getDynamicRevGrowth block.")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success")

if __name__ == '__main__':
    main()
