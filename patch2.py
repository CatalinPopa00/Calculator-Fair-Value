import sys
import re

def main():
    file_path = 'c:/Users/Snoozie/Downloads/Calculator-Fair-Value/Calculator-Fair-Value/app.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. We need to inject the getDynamicEpsGrowth and getDynamicRevGrowth helpers at the top of updateFairValue()
    update_func_start = "const updateFairValue = () => {"
    
    helpers = """const updateFairValue = () => {
        const getDynamicEpsGrowth = () => {
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
        };
        
        const getDynamicRevGrowth = () => {
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
        };
        
        window._getDynamicEpsGrowth = getDynamicEpsGrowth;
        window._getDynamicRevGrowth = getDynamicRevGrowth;
"""
    if update_func_start in content:
        content = content.replace(update_func_start, helpers, 1)

    # 2. Update PEG Analyst Logic
    old_peg_analyst = """            if (pegSrc === 'analyst') {
                const eList = globalData.eps_estimates || [];
                const ests = eList.filter(e => e && e.status !== 'reported');
                if (_currentScenario === 'bear') {
                    if (ests.length >= 2 && ests[0].low != null && ests[0].yearAgo != null && ests[1].low != null) {
                        const g1 = (ests[0].low - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                        const g2 = (ests[1].low - ests[0].low) / Math.abs(ests[0].low);
                        usedGrowth = (g1 + g2) / 2.0;
                    } else if (ests.length === 1 && ests[0].low != null && ests[0].yearAgo != null) {
                        usedGrowth = (ests[0].low - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                    }
                } else if (_currentScenario === 'bull') {
                    if (ests.length >= 2 && ests[0].high != null && ests[0].yearAgo != null && ests[1].high != null) {
                        const g1 = (ests[0].high - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                        const g2 = (ests[1].high - ests[0].high) / Math.abs(ests[0].high);
                        usedGrowth = (g1 + g2) / 2.0;
                    } else if (ests.length === 1 && ests[0].high != null && ests[0].yearAgo != null) {
                        usedGrowth = (ests[0].high - ests[0].yearAgo) / Math.abs(ests[0].yearAgo);
                    }
                }
            } else if (pegSrc === '5ycagr') {"""
            
    new_peg_analyst = """            if (pegSrc === 'analyst') {
                usedGrowth = getDynamicEpsGrowth();
            } else if (pegSrc === '5ycagr') {"""
            
    if old_peg_analyst in content:
        content = content.replace(old_peg_analyst, new_peg_analyst)
    
    old_peg_calc = """            } else if (pegSrc === 'analyst') {
                pegVal = currentFormulaData.peg.fair_value;
                // For analyst PEG, current PEG display still reacts to price
                const staticPe = currentFormulaData.peg.current_pe || (eps > 0 ? (globalData.current_price / eps) : 0);
                currentPegToDisplay = staticPe / (usedGrowth * 100);
                
                if (pegVal != null) {
                    pegMos = ((pegVal - globalData.current_price) / globalData.current_price) * 100;
                }
                
                currentFormulaData.peg.dynamic_growth = usedGrowth;
                currentFormulaData.peg.dynamic_fv = pegVal;
                currentFormulaData.peg.dynamic_peg = currentPegToDisplay;
            }"""
            
    new_peg_calc = """            } else if (pegSrc === 'analyst') {
                // Completely dynamic recalculation for Analyst PEG
                const staticPe = currentFormulaData.peg.current_pe || (eps > 0 ? (globalData.current_price / eps) : 0);
                const originalPeg = staticPe / (usedGrowth * 100);
                // Calculate Dynamic Fair Value
                pegVal = _realApiPrice * (targetPeg / originalPeg);
                
                const simPe = (eps > 0) ? (globalData.current_price / eps) : (staticPe * (globalData.current_price / _realApiPrice));
                currentPegToDisplay = simPe / (usedGrowth * 100);
                
                if (pegVal != null) {
                    pegMos = ((pegVal - globalData.current_price) / globalData.current_price) * 100;
                }
                
                currentFormulaData.peg.dynamic_growth = usedGrowth;
                currentFormulaData.peg.dynamic_fv = pegVal;
                currentFormulaData.peg.dynamic_peg = currentPegToDisplay;
            }"""
            
    if old_peg_calc in content:
        content = content.replace(old_peg_calc, new_peg_calc)

    # 3. Update Peter Lynch (Forward Multiple) Logic
    old_lynch = """            let usedGrowth = pl.eps_growth_estimated || 0.05;
            let baseEps = pl.valuation_eps || pl.trailing_eps || 0;
            let targetEps = baseEps * Math.pow(1 + usedGrowth, 3); // v288: Restored 3Y Compounded Projection

            if (epsSource === '5ycagr') {
                usedGrowth = pl.eps_growth_5y_cagr || usedGrowth;
                targetEps = baseEps * Math.pow(1 + usedGrowth, 3);
            } else if (epsSource === 'historical') {"""
            
    new_lynch = """            let usedGrowth = pl.eps_growth_estimated || 0.05;
            let baseEps = pl.valuation_eps || pl.trailing_eps || 0;
            
            if (epsSource === 'analyst') {
                usedGrowth = getDynamicEpsGrowth();
            }
            if (epsSource === '5ycagr') {
                usedGrowth = pl.eps_growth_5y_cagr || usedGrowth;
            } else if (epsSource === 'historical') {"""
            
    if old_lynch in content:
        content = content.replace(old_lynch, new_lynch)
    
    old_lynch_target_eps = """                targetEps = baseEps * Math.pow(1 + usedGrowth, 3);
            } else if (epsSource === 'custom') {"""
    new_lynch_target_eps = """            } else if (epsSource === 'custom') {"""
    if old_lynch_target_eps in content:
        content = content.replace(old_lynch_target_eps, new_lynch_target_eps)
    
    old_lynch_custom = """                const rawG = document.getElementById('lynch-custom-growth').value;
                usedGrowth = (rawG === '' || isNaN(parseFloat(rawG))) ? 0.20 : parseFloat(rawG) / 100;
                targetEps = baseEps * Math.pow(1 + usedGrowth, 3);
            }"""
    new_lynch_custom = """                const rawG = document.getElementById('lynch-custom-growth').value;
                usedGrowth = (rawG === '' || isNaN(parseFloat(rawG))) ? 0.20 : parseFloat(rawG) / 100;
            }
            let targetEps = baseEps * Math.pow(1 + usedGrowth, 3);"""
    if old_lynch_custom in content:
        content = content.replace(old_lynch_custom, new_lynch_custom)

    old_lynch_mult = """            let selectedMult = 20; 
            if (multVal === 'system') {
                selectedMult = usedGrowth * 100;
            } else if (multVal === 'historical') {"""
    new_lynch_mult = """            let selectedMult = 20; 
            if (multVal === 'system') {
                selectedMult = Math.min(Math.max(usedGrowth * 100, 15), 25);
            } else if (multVal === 'historical') {"""
    if old_lynch_mult in content:
        content = content.replace(old_lynch_mult, new_lynch_mult)
    
    old_lynch_fallback = """            } else {
                // Fallback just in case
                selectedMult = usedGrowth * 100;
            }"""
    new_lynch_fallback = """            } else {
                // Fallback just in case
                selectedMult = Math.min(Math.max(usedGrowth * 100, 15), 25);
            }"""
    if old_lynch_fallback in content:
        content = content.replace(old_lynch_fallback, new_lynch_fallback)


    # 4. Update DCF Logic
    revG_pattern = r'const getRevG = \(\) => \{.*?\};\n                        const g13 = Math\.round\(getRevG\(\) \* 1000\) \/ 1000;'
    content = re.sub(revG_pattern, r'const g13 = Math.round(getDynamicRevGrowth() * 1000) / 1000;', content, flags=re.DOTALL)
    
    old_dcf_eps = """                    } else {
                        g = currentFormulaData.dcf.eps_growth_applied || 0.10;
                    }"""
    new_dcf_eps = """                    } else {
                        const epsG13 = Math.round(getDynamicEpsGrowth() * 1000) / 1000;
                        const epsG46 = epsG13 * 0.75;
                        const epsG78 = epsG13 * 0.50;
                        const epsG910 = epsG13 * 0.25;
                        g = [];
                        for (let y = 1; y <= 10; y++) {
                            if (y <= 3) g.push(epsG13);
                            else if (y <= 6) g.push(epsG46);
                            else if (y <= 8) g.push(epsG78);
                            else g.push(epsG910);
                        }
                    }"""
    if old_dcf_eps in content:
        content = content.replace(old_dcf_eps, new_dcf_eps)


    # 5. Export currentPegToDisplay
    old_export_peg = """        // --- Sync Profile & Metrics Table PEG with Card PEG ---
        const pegTableVal = document.getElementById('metric-val-peg');
        if (pegTableVal && currentPegToDisplay != null && !_simulating) {
            pegTableVal.textContent = currentPegToDisplay.toFixed(2);
        }

        // --- Dynamic UI Re-renders for Scenarios ---"""
    new_export_peg = """        // --- Sync Profile & Metrics Table PEG with Card PEG ---
        const pegTableVal = document.getElementById('metric-val-peg');
        if (pegTableVal && currentPegToDisplay != null && !_simulating) {
            pegTableVal.textContent = currentPegToDisplay.toFixed(2);
        }
        
        window._currentPegToDisplay = currentPegToDisplay;

        // --- Dynamic UI Re-renders for Scenarios ---"""
    if old_export_peg in content:
        content = content.replace(old_export_peg, new_export_peg)


    # 6. Profile Section table
    old_profile_peg = """${metricRow('PEG', prof.peg_ratio ? prof.peg_ratio.toFixed(2) : 'N/A')}"""
    new_profile_peg = """${metricRow('PEG', window._currentPegToDisplay != null ? window._currentPegToDisplay.toFixed(2) : (prof.peg_ratio ? prof.peg_ratio.toFixed(2) : 'N/A'))}"""
    if old_profile_peg in content:
        content = content.replace(old_profile_peg, new_profile_peg)
        
    old_profile_peg2 = """${metricRow('PEG', prof.peg_ratio ? prof.peg_ratio.toFixed(2) : 'N/A', '', 'right')}"""
    new_profile_peg2 = """${metricRow('PEG', window._currentPegToDisplay != null ? window._currentPegToDisplay.toFixed(2) : (prof.peg_ratio ? prof.peg_ratio.toFixed(2) : 'N/A'), '', 'right')}"""
    if old_profile_peg2 in content:
        content = content.replace(old_profile_peg2, new_profile_peg2)
        

    # 7. Update Relative Valuation Dynamic variables
    old_rel_dyn = """            if (_currentScenario === 'bear' || _currentScenario === 'bull') {
                const eList = globalData.eps_estimates || [];
                const eEsts = eList.filter(e => e && e.status !== 'reported');
                if (eEsts.length >= 2) {
                    const y1 = _currentScenario === 'bear' ? eEsts[0].low : eEsts[0].high;
                    const y2 = _currentScenario === 'bear' ? eEsts[1].low : eEsts[1].high;
                    if (y1 != null && y2 != null) company_eps = (y1 + y2) / 2.0;
                    else if (y1 != null) company_eps = y1;
                } else if (eEsts.length === 1) {
                    const y1 = _currentScenario === 'bear' ? eEsts[0].low : eEsts[0].high;
                    if (y1 != null) company_eps = y1;
                }
                
                const rList = globalData.rev_estimates || [];
                const rEsts = rList.filter(e => e && e.status !== 'reported');
                let avgRev = null;
                if (rEsts.length >= 2) {
                    const r1 = _currentScenario === 'bear' ? rEsts[0].low : rEsts[0].high;
                    const r2 = _currentScenario === 'bear' ? rEsts[1].low : rEsts[1].high;
                    if (r1 != null && r2 != null) avgRev = (r1 + r2) / 2.0;
                    else if (r1 != null) avgRev = r1;
                } else if (rEsts.length === 1) {
                    const r1 = _currentScenario === 'bear' ? rEsts[0].low : rEsts[0].high;
                    if (r1 != null) avgRev = r1;
                }
                if (avgRev != null && company_shares > 0) company_sales_share = avgRev / company_shares;
            }"""
            
    new_rel_dyn = """            if (_currentScenario === 'bear' || _currentScenario === 'bull') {
                const eList = globalData.eps_estimates || [];
                const eEsts = eList.filter(e => e && e.status !== 'reported');
                if (eEsts.length >= 2) {
                    const y1 = _currentScenario === 'bear' ? eEsts[0].low : eEsts[0].high;
                    const y2 = _currentScenario === 'bear' ? eEsts[1].low : eEsts[1].high;
                    if (y1 != null && y2 != null) company_eps = (y1 + y2) / 2.0;
                    else if (y1 != null) company_eps = y1;
                } else if (eEsts.length === 1) {
                    const y1 = _currentScenario === 'bear' ? eEsts[0].low : eEsts[0].high;
                    if (y1 != null) company_eps = y1;
                }
                
                const rList = globalData.rev_estimates || [];
                const rEsts = rList.filter(e => e && e.status !== 'reported');
                let avgRev = null;
                if (rEsts.length >= 2) {
                    const r1 = _currentScenario === 'bear' ? rEsts[0].low : rEsts[0].high;
                    const r2 = _currentScenario === 'bear' ? rEsts[1].low : rEsts[1].high;
                    if (r1 != null && r2 != null) avgRev = (r1 + r2) / 2.0;
                    else if (r1 != null) avgRev = r1;
                } else if (rEsts.length === 1) {
                    const r1 = _currentScenario === 'bear' ? rEsts[0].low : rEsts[0].high;
                    if (r1 != null) avgRev = r1;
                }
                if (avgRev != null && company_shares > 0) company_sales_share = avgRev / company_shares;
            }
            rel.dynamic_company_eps = company_eps;
            rel.dynamic_company_sales_share = company_sales_share;
            """
    if old_rel_dyn in content:
        content = content.replace(old_rel_dyn, new_rel_dyn)
        
    old_implied_eps = """const eps = (r.company_fwd_eps || 0) > 0 ? r.company_fwd_eps : (r.company_eps || 0);"""
    new_implied_eps = """const eps = r.dynamic_company_eps != null ? r.dynamic_company_eps : ((r.company_fwd_eps || 0) > 0 ? r.company_fwd_eps : (r.company_eps || 0));"""
    if old_implied_eps in content:
        content = content.replace(old_implied_eps, new_implied_eps)
        
    old_implied_sales = """const salesS = explicit_fwd_ps > 0 ? (_realApiPrice / explicit_fwd_ps) : (r.company_sales_share || 0);"""
    new_implied_sales = """const salesS = r.dynamic_company_sales_share != null ? r.dynamic_company_sales_share : (explicit_fwd_ps > 0 ? (_realApiPrice / explicit_fwd_ps) : (r.company_sales_share || 0));"""
    if old_implied_sales in content:
        content = content.replace(old_implied_sales, new_implied_sales)

    # 8. Modals refreshing logic
    old_end = """        // --- Dynamic UI Re-renders for Scenarios ---
        if (window._renderProfile) window._renderProfile();
        if (window._renderEstimatesTable) window._renderEstimatesTable();
    };"""
    new_end = """        // --- Dynamic UI Re-renders for Scenarios ---
        if (window._renderProfile) window._renderProfile();
        if (window._renderEstimatesTable) window._renderEstimatesTable();
        
        // If View Data modal is open, simulate a click on the corresponding trigger to refresh it
        const dataModal = document.getElementById('data-modal');
        if (dataModal && dataModal.style.display === 'flex') {
            const activeTitle = document.getElementById('modal-title')?.textContent || '';
            let btnSelector = null;
            if (activeTitle.includes('Discounted Cash Flow')) btnSelector = 'button[data-method="dcf"]';
            else if (activeTitle.includes('Triangulation')) btnSelector = 'button[data-method="relative"]';
            else if (activeTitle.includes('Forward Multiple')) btnSelector = 'button[data-method="peter_lynch"]';
            else if (activeTitle.includes('PEG Valuation')) btnSelector = 'button[data-method="peg"]';
            
            if (btnSelector) {
                const btn = document.querySelector(btnSelector);
                if (btn) btn.click();
            }
        }
        
        // Refresh Comparison Modal if open
        const compModal = document.getElementById('comparison-modal');
        if (compModal && compModal.style.display === 'flex') {
            const prof = globalData.company_profile;
            if (prof && typeof renderComparisonModal === 'function') {
                renderComparisonModal(prof);
            }
        }
    };"""
    if old_end in content:
        content = content.replace(old_end, new_end)


    # 9. Ensure renderComparisonModal uses dynamic scenario values
    old_render_comp = """        const mainComp = {
            ticker: prof.ticker || currentTicker,
            name: prof.name || 'Current',
            market_cap: prof.market_cap,
            pe_ratio: prof.fwd_eps > 0 ? (_realApiPrice / prof.fwd_eps) : prof.trailing_pe,
            fwd_pe: prof.fwd_eps > 0 ? (_realApiPrice / prof.fwd_eps) : null,
            peg_ratio: prof.peg_ratio,
            eps: prof.trailing_eps,
            fwd_eps: prof.fwd_eps,
            ps_ratio: prof.ps_ratio,
            revenue: globalData.revenue || (prof.market_cap && prof.ps_ratio && prof.ps_ratio > 0 ? prof.market_cap / prof.ps_ratio : null),
            pfcf_ratio: mainPfcf,
            fcf: mainFcf || (prof.market_cap && mainPfcf && mainPfcf > 0 ? prof.market_cap / mainPfcf : null),
            fcf_growth: prof.historic_fcf_growth,
            margin: prof.operating_margin,
            rev_growth: prof.revenue_growth,
            eps_growth: prof.earnings_growth
        };"""
        
    new_render_comp = """        let dynFwdEps = prof.fwd_eps;
        let dynRevGrowth = prof.revenue_growth;
        let dynEpsGrowth = prof.earnings_growth;
        
        if (window._currentScenario === 'bear' || window._currentScenario === 'bull') {
            if (window._getDynamicEpsGrowth) dynEpsGrowth = window._getDynamicEpsGrowth();
            if (window._getDynamicRevGrowth) dynRevGrowth = window._getDynamicRevGrowth();
            
            // Get dynamic fwd eps based on scenario from eps_estimates (FY 1)
            const eList = globalData.eps_estimates || [];
            const eEsts = eList.filter(e => e && e.status !== 'reported');
            if (eEsts.length > 0) {
                dynFwdEps = window._currentScenario === 'bear' ? eEsts[0].low : eEsts[0].high;
            }
        }

        const mainComp = {
            ticker: prof.ticker || currentTicker,
            name: prof.name || 'Current',
            market_cap: prof.market_cap,
            pe_ratio: prof.fwd_eps > 0 ? (_realApiPrice / prof.fwd_eps) : prof.trailing_pe,
            fwd_pe: dynFwdEps > 0 ? (_realApiPrice / dynFwdEps) : null,
            peg_ratio: prof.peg_ratio,
            eps: prof.trailing_eps,
            fwd_eps: dynFwdEps,
            ps_ratio: prof.ps_ratio,
            revenue: globalData.revenue || (prof.market_cap && prof.ps_ratio && prof.ps_ratio > 0 ? prof.market_cap / prof.ps_ratio : null),
            pfcf_ratio: mainPfcf,
            fcf: mainFcf || (prof.market_cap && mainPfcf && mainPfcf > 0 ? prof.market_cap / mainPfcf : null),
            fcf_growth: prof.historic_fcf_growth,
            margin: prof.operating_margin,
            rev_growth: dynRevGrowth,
            eps_growth: dynEpsGrowth
        };"""
    if old_render_comp in content:
        content = content.replace(old_render_comp, new_render_comp)
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patch applied successfully.")

if __name__ == '__main__':
    main()
