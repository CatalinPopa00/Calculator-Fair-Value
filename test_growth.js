const globalData = {
    rev_estimates: [
        { period: "FY 2026", avg: 215.94, status: "reported" },
        { period: "FY 2027", avg: 391.49, low: 357.21, high: 415.52, status: "estimate", growth: 0.813 },
        { period: "FY 2028", avg: 547.67, low: 416.40, high: 710.01, status: "estimate", growth: 0.399 }
    ],
    company_profile: { revenue_growth: 0.813 }
};
let _currentScenario = 'bear';

const getDynamicRevGrowth = () => {
    const rItems = globalData.rev_estimates || [];
    let growths = [];
    let prevRevVal = null;
    
    rItems.forEach((item) => {
        if (!item) return;
        const isAnchor = item.status === 'reported';
        let scenarioVal = item.avg;
        if (!isAnchor) {
            if (_currentScenario === 'bear' && item.low != null) scenarioVal = item.low;
            if (_currentScenario === 'bull' && item.high != null) scenarioVal = item.high;
        }
        
        if (!isAnchor) {
            let dynamicBase = prevRevVal;
            if (scenarioVal != null && dynamicBase != null && dynamicBase !== 0) {
                let g = (parseFloat(scenarioVal) / parseFloat(dynamicBase)) - 1;
                growths.push(g);
            } else if (item.growth != null) {
                growths.push(parseFloat(item.growth));
            }
        }
        prevRevVal = scenarioVal;
    });
    
    if (growths.length >= 2) return (growths[0] + growths[1]) / 2.0;
    if (growths.length === 1) return growths[0];
    
    const revFallback = globalData?.company_profile?.revenue_growth || 0.08;
    if (_currentScenario === 'bear') return revFallback * 0.70;
    if (_currentScenario === 'bull') return revFallback * 1.30;
    return revFallback;
};

console.log("Bear: ", getDynamicRevGrowth());
_currentScenario = 'base';
console.log("Base: ", getDynamicRevGrowth());
_currentScenario = 'bull';
console.log("Bull: ", getDynamicRevGrowth());
