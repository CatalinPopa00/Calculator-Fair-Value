import os

js_snippet = '''        // --- 4. Predictive Scoring Logic (v70: Matches backend scoring.py thresholds) ---
        if (currentBuyBreakdown) {
            currentBuyBreakdown.forEach(item => {
                const metric = item.metric || '';
                let newPts = item.points_awarded;

                // Sector detection (matches scoring.py logic)
                const industry = (prof.industry || '').toLowerCase();
                const sector = (prof.sector || '').toLowerCase();
                
                const isBank = industry.includes('bank') || industry.includes('credit services') || industry.includes('savings');
                const isFin = sector.includes('financial');
                const isInsurance = industry.includes('insurance');
                const isREIT = sector.includes('real estate') || sector.includes('reit');
                const isEnergy = sector.includes('energy') || sector.includes('basic materials') || sector.includes('materials');
                const isUtilities = sector.includes('utilities') || sector.includes('telecommunication') || industry.includes('telecom');
                const isDefensive = sector.includes('consumer defensive') || sector.includes('staples') || sector.includes('healthcare') || sector.includes('health care');
                const isTech = sector.includes('technology') || sector.includes('communication services') || industry.includes('software') || industry.includes('internet');

                // Extract simulation anchors
                const eps_5yr_g = cleanPercent(globalData.company_profile.eps_growth_5y_consensus || globalData.company_profile.eps_5yr_growth);
                const rev_g_val = cleanPercent(globalData.company_profile.revenue_growth || 0);
                const fwd_growth = eps_5yr_g > 0 ? eps_5yr_g : rev_g_val;
                
                const fwd_pe = parseFloat(globalData.company_profile.forward_pe) || 0;
                
                // For live simulation, recalculate simulated P/E based on forward or trailing
                let simulatedPE = scoringPE;
                let simulatedFwdPE = 0;
                if (fwd_pe > 0 && prof.adjusted_eps > 0) {
                    // if they had forward PE, simulate it using the same implied forward EPS
                    const implied_fwd_eps = _realApiPrice / fwd_pe;
                    simulatedFwdPE = simPrice / implied_fwd_eps;
                }
                
                let activePE = simulatedPE;
                if (isTech || isDefensive) {
                    if (simulatedFwdPE > 0) activePE = simulatedFwdPE;
                } else {
                    if (simulatedFwdPE > 0) activePE = simulatedFwdPE;
                }
                
                // Guard Clause Universal
                if ((metric.includes('P/E Ratio') || metric.includes('EV / EBITDA') || metric.includes('P/S Ratio') || metric.includes('Price-to-Book') || metric.includes('P/AFFO')) && (activePE < 0 || newEvEbitda < 0 || newPS < 0 || newPB < 0)) {
                     // handled below per metric, but generally 0 pts
                }

                if (metric.includes('Margin of Safety')) {
                    if (isFin && isBank) {
                        newPts = (newMos > 15) ? 25 : ((newMos > 5) ? 25*(14.9/25.0) : (newMos >= -5 ? 10 : 0));
                    } else if (isInsurance || isREIT || isEnergy || isUtilities || isDefensive || isTech) {
                        newPts = (newMos > 15) ? 30 : ((newMos > 5) ? 30*(14.9/25.0) : (newMos >= -5 ? 12 : 0));
                    } else {
                        newPts = (newMos > 15) ? 30 : ((newMos > 5) ? 30*(14.9/25.0) : (newMos >= -5 ? 12 : 0));
                    }
                    item.value = formatPercent(newMos);
                } else if (metric.includes('P/E Ratio')) {
                    let pts = 0;
                    if (activePE > 0) {
                        if (isFin && isBank) {
                            if (activePE <= 13) pts = 20;
                            else if (activePE <= 15) pts = 10;
                        } else if (isInsurance) {
                            if (activePE <= 15) pts = 20;
                            else if (activePE <= 18) pts = 10;
                        } else if (isEnergy) {
                            if (activePE < 6) pts = 5;
                            else if (activePE <= 15) pts = 15;
                            else if (activePE <= 20) pts = 10;
                        } else if (isUtilities) {
                            if (activePE <= 15) pts = 15;
                            else if (activePE <= 18) pts = 7.5;
                        } else if (isDefensive) {
                            if (activePE <= 20) pts = 20;
                            else if (activePE <= 25) pts = 10;
                            if (pts === 0 && activePE > 0 && pegUsedGrowth > 0) {
                                const peg = activePE / (fwd_growth);
                                if (peg > 0 && peg <= 1.2 && fwd_growth >= 15.0) pts = 10;
                            }
                        } else if (isTech) {
                            if (activePE <= 25.0) pts = 20;
                            else if (activePE <= 25.0 * 1.3) pts = 10;
                            if (pts === 0 && activePE > 0 && pegUsedGrowth > 0) {
                                const peg = activePE / (fwd_growth);
                                if (peg > 0 && peg <= 1.2 && fwd_growth >= 20.0) pts = 10;
                            }
                        } else {
                            // Industrials
                            if (activePE <= 18) pts = 20;
                            else if (activePE <= 22) pts = 10;
                            if (pts === 0 && activePE > 0 && pegUsedGrowth > 0) {
                                const peg = activePE / (fwd_growth);
                                if (peg > 0 && peg <= 1.2 && fwd_growth >= 15.0) pts = 10;
                            }
                        }
                    }
                    newPts = pts;
                    item.value = activePE > 0 ? activePE.toFixed(2) + 'x' : '0.00x';
                } else if (metric.includes('EV / EBITDA')) {
                    let pts = 0;
                    if (newEvEbitda > 0) {
                        if (isEnergy) {
                            if (newEvEbitda <= 6.0) pts = 20;
                            else if (newEvEbitda <= 9.0) pts = 10;
                        } else if (isUtilities) {
                            if (newEvEbitda <= 10.0) pts = 20;
                            else if (newEvEbitda <= 14.0) pts = 10;
                        } else if (isDefensive) {
                            if (newEvEbitda <= 14.0) pts = 15;
                            else if (newEvEbitda <= 18.0) pts = 7.5;
                            if (pts === 0 && newEvEbitda > 0 && pegUsedGrowth > 0) {
                                const peg = activePE / (fwd_growth);
                                if (peg > 0 && peg <= 1.2 && fwd_growth >= 15.0) pts = 7.5;
                            }
                        } else if (isTech) {
                            if (newEvEbitda <= 18.0) pts = 10;
                            else if (newEvEbitda <= 25.0) pts = 5;
                            if (pts === 0 && newEvEbitda > 0 && pegUsedGrowth > 0) {
                                const peg = activePE / (fwd_growth);
                                if (peg > 0 && peg <= 1.2 && fwd_growth >= 20.0) pts = 5;
                            }
                        } else {
                            if (newEvEbitda <= 12.0) pts = 10;
                            else if (newEvEbitda <= 16.0) pts = 5;
                            if (pts === 0 && newEvEbitda > 0 && pegUsedGrowth > 0) {
                                const peg = activePE / (fwd_growth);
                                if (peg > 0 && peg <= 1.2 && fwd_growth >= 15.0) pts = 5;
                            }
                        }
                    }
                    newPts = pts;
                    item.value = newEvEbitda > 0 ? newEvEbitda.toFixed(2) + 'x' : '0.00x';
                } else if (metric.includes('Price-to-Book')) {
                    let pts = 0;
                    if (newPB > 0) {
                        if (isFin && isBank) {
                            if (newPB < 1.5) pts = 20;
                            else if (newPB <= 2.0) pts = 10;
                        } else if (isInsurance) {
                            if (newPB < 1.5) pts = 25;
                            else if (newPB <= 2.0) pts = 12.5;
                        } else if (isEnergy) {
                            if (newPB <= 1.5) pts = 20;
                            else if (newPB <= 2.5) pts = 10;
                        } else {
                            if (newPB <= 2.0) pts = 10;
                            else if (newPB <= 3.0) pts = 5;
                        }
                    }
                    newPts = pts;
                    item.value = newPB > 0 ? newPB.toFixed(2) + 'x' : '0.00x';
                } else if (metric.includes('P/S Ratio')) {
                    const target_pe = getTargetPe(sector, industry);
                    const margin = cleanPercent(globalData.company_profile.ebit_margin || globalData.company_profile.operating_margin || 0); 
                    const target_ps = target_pe * (margin / 100.0);
                    let pts = 0;
                    if (newPS > 0) {
                        if (margin < 0) {
                            if (fwd_growth > 20 && newPS <= 5.0) pts = 5;
                        } else {
                            if (newPS <= target_ps) pts = 10;
                            else if (newPS <= target_ps * 1.5) pts = 5;
                        }
                    }
                    newPts = pts;
                    item.value = newPS > 0 ? newPS.toFixed(2) + 'x' : '0.00x';
                } else if (metric.includes('Dividend Yield')) {
                    const dyPct = newDivYield * 100;
                    if (isREIT) newPts = dyPct > 5 ? 15 : (dyPct >= 3 ? 7.5 : 0);
                    else if (isFin && isBank) newPts = dyPct > 4 ? 15 : (dyPct >= 2 ? 7.5 : 0);
                    else if (isInsurance) newPts = dyPct > 3 ? 15 : (dyPct >= 1.5 ? 7.5 : 0);
                    else if (isEnergy) newPts = dyPct > 4 ? 15 : (dyPct >= 2 ? 7.5 : 0);
                    else if (isUtilities) newPts = dyPct > 4 ? 25 : (dyPct >= 2.5 ? 12.5 : 0);
                    else newPts = 0;
                    item.value = dyPct.toFixed(1) + '%';
                } else if (metric.includes('PEG Ratio')) {
                    const newPEG = (fwd_growth > 0 && activePE > 0) ? activePE / fwd_growth : 0;
                    if (isFin && isBank) newPts = (newPEG > 0 && newPEG < 1.0) ? 10 : ((newPEG > 0 && newPEG <= 1.5) ? 5 : 0);
                    else if (isDefensive) newPts = (newPEG > 0 && newPEG < 1.5) ? 20 : ((newPEG > 0 && newPEG <= 2.0) ? 10 : 0);
                    else if (isTech) newPts = (newPEG > 0 && newPEG < 1.5) ? 10 : ((newPEG > 0 && newPEG <= 2.0) ? 5 : 0);
                    else newPts = (newPEG > 0 && newPEG < 1.0) ? 10 : ((newPEG > 0 && newPEG <= 1.5) ? 5 : 0);
                    item.value = newPEG > 0 ? newPEG.toFixed(2) + 'x' : '0.00x';
                } else if (metric.includes('P/AFFO')) {
                    const affoPerShare = prof.price_to_affo > 0 ? (_originalPrice / prof.price_to_affo) : 0;
                    const newPAFFO = affoPerShare > 0 ? simPrice / affoPerShare : 0;
                    let pts = 0;
                    if (newPAFFO > 0) {
                        if (newPAFFO <= 15) pts = 20;
                        else if (newPAFFO <= 18) pts = 10;
                    }
                    newPts = pts;
                    item.value = newPAFFO > 0 ? newPAFFO.toFixed(2) + 'x' : '0.00x';
                } else if (metric.includes('Rev Growth') || metric.includes('EPS Growth') || metric.includes('AFFO Growth')) {
                    // Growth points are static in simulation since simulation only affects price derivatives
                    item.value = fwd_growth > 0 ? fwd_growth.toFixed(1) + '%' : '0.0%';
                }

                item.points_awarded = Math.min(newPts, item.max_points);
            });
        }'''

import re

for filename in ['app.js', 'vercel_app.js', 'vercel_app_v234.js']:
    filepath = os.path.join(r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value", filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We replace the entire block from "// --- 4. Predictive Scoring Logic" to "item.points_awarded = Math.min(newPts, item.max_points);\n            });\n        }"
    pattern = r'// --- 4\. Predictive Scoring Logic.*?} \n                item\.points_awarded = Math\.min\(newPts, item\.max_points\);\n            \}\);\n        \}'
    
    # Let's use a simpler approach: splitting
    start_str = "// --- 4. Predictive Scoring Logic"
    end_str = "        // --- 5. Global Visual Re-sync ---"
    
    if start_str in content and end_str in content:
        before = content.split(start_str)[0]
        after = content.split(end_str)[1]
        
        new_content = before + js_snippet + "\n\n" + end_str + after
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filename}")
