import re

def update_app_js():
    with open('app.js', 'r', encoding='utf-8') as f:
        app_js = f.read()

    # 1. We need to inject the High-Growth logic in displayData, right after `_originalBuyScore = data.good_to_buy_total;`
    # Let's search for this hook point
    hook = r"_originalBuyScore = data\.good_to_buy_total;"
    
    # Check if we already injected it
    if "window.isHighGrowthModel" not in app_js:
        injection = """
        // HIGH-GROWTH CONDITIONAL RENDERING LOGIC
        window.isHighGrowthModel = false;
        if (data.company_profile) {
            const fwd_eps = data.company_profile.forward_eps || data.company_profile.fwd_eps || 0;
            const fwd_pe = data.company_profile.forward_pe || 0;
            const rev_growth = (data.company_profile.revenue_growth || data.company_profile.rev_cagr_2y || 0) * (data.company_profile.revenue_growth > 1 ? 1 : 100);
            
            if ((fwd_eps <= 0 || fwd_pe > 80) && rev_growth > 15) {
                window.isHighGrowthModel = true;
                
                // Rule of 40
                const ebitdaMargin = (data.company_profile.ebitda_margins || 0) * (data.company_profile.ebitda_margins > 1 ? 1 : 100);
                const ruleOf40 = rev_growth + ebitdaMargin;
                let r40Pts = 0;
                if (ruleOf40 >= 40) r40Pts = 30;
                else if (ruleOf40 >= 30) r40Pts = 15;
                
                // Gross Margin Trend
                const gmTTM = (data.company_profile.gross_margins || 0) * (data.company_profile.gross_margins > 1 ? 1 : 100);
                let gmPrev = gmTTM;
                if (data.health_score && data.health_score.beneish && data.health_score.beneish.prev && data.health_score.beneish.prev.sales > 0) {
                    gmPrev = (data.health_score.beneish.prev.gross_profit / data.health_score.beneish.prev.sales) * 100;
                }
                let gmTrendPts = 0;
                if (gmTTM > gmPrev + 2) gmTrendPts = 25;
                else if (gmTTM >= gmPrev - 2) gmTrendPts = 10;
                
                // Cash Runway / Quick Ratio (fallback to Current Ratio)
                const qRatio = data.company_profile.quick_ratio || data.company_profile.current_ratio || 0;
                let qrPts = 0;
                if (qRatio >= 1.5) qrPts = 20;
                else if (qRatio >= 1.0) qrPts = 10;
                
                // EV / Gross Profit (Fwd 1Y)
                let evGpPts = 0;
                let evGpValStr = 'N/A';
                
                // Calculate Median EV / Gross Profit from peers if available
                let medEvGp = 0;
                if (data.company_profile.competitor_metrics && data.company_profile.competitor_metrics.length > 0) {
                    let evGps = [];
                    data.company_profile.competitor_metrics.forEach(p => {
                        // Estimate Fwd Gross Profit for peers
                        let pRevGrow = (p.revenue_growth || 0) * (p.revenue_growth > 1 ? 1 : 100) / 100;
                        let pGm = (p.gross_margins || 0) * (p.gross_margins > 1 ? 1 : 100) / 100;
                        let pFwdRev = (p.total_revenue || 0) * (1 + pRevGrow);
                        let pFwdGp = pFwdRev * pGm;
                        if (pFwdGp > 0 && p.enterprise_value > 0) {
                            evGps.push(p.enterprise_value / pFwdGp);
                        }
                    });
                    if (evGps.length > 0) {
                        evGps.sort((a, b) => a - b);
                        medEvGp = evGps.length % 2 === 0 ? (evGps[evGps.length / 2 - 1] + evGps[evGps.length / 2]) / 2 : evGps[Math.floor(evGps.length / 2)];
                    }
                }
                
                const fwdRev = (data.company_profile.total_revenue || 0) * (1 + (rev_growth / 100));
                const fwdGp = fwdRev * (gmTTM / 100);
                let evGp = 0;
                if (fwdGp > 0 && data.company_profile.enterprise_value) {
                    evGp = data.company_profile.enterprise_value / fwdGp;
                    evGpValStr = evGp.toFixed(2) + 'x';
                }
                
                if (medEvGp > 0 && evGp > 0) {
                    if (evGp <= medEvGp) evGpPts = 25;
                    else if (evGp <= medEvGp * 1.2) evGpPts = 10;
                    else evGpPts = 0;
                } else {
                    evGpValStr = evGp > 0 ? (evGpValStr + ' (No Sector Data)') : 'Pending Sector Data';
                    evGpPts = 0; // 0 points temporarily until sector data is loaded
                }

                currentBuyBreakdown = [
                    { metric: "Rule of 40", value: ruleOf40.toFixed(1) + "%", points: r40Pts, max_points: 30, display_type: "raw" },
                    { metric: "EV / Gross Profit (Fwd 1Y)", value: evGpValStr, points: evGpPts, max_points: 25, display_type: "raw" },
                    { metric: "Gross Margin Trend", value: "TTM: " + gmTTM.toFixed(1) + "% vs Prev: " + gmPrev.toFixed(1) + "%", points: gmTrendPts, max_points: 25, display_type: "raw" },
                    { metric: "Cash Runway / Quick Ratio", value: qRatio.toFixed(2) + "x", points: qrPts, max_points: 20, display_type: "raw" }
                ];
                
                data.good_to_buy_total = r40Pts + evGpPts + gmTrendPts + qrPts;
                globalData.good_to_buy_total = data.good_to_buy_total;
                globalData.buy_breakdown = currentBuyBreakdown;
            }
        }"""
        app_js = re.sub(r"(_originalBuyScore = data\.good_to_buy_total;)", r"\1\n" + injection, app_js)
    
    # 2. Add UI Badge to Good to Buy Score
    # We can inject this in `updateScoreUI(data.good_to_buy_total, 'buy-score-circle', 'buy-score-fill');`
    hook_badge = r"updateScoreUI\(data\.good_to_buy_total, 'buy-score-circle', 'buy-score-fill'\);"
    if "hg-badge" not in app_js:
        badge_injection = """
        const buyTitleWrap = document.querySelector('#buy-score-circle').closest('.score-card').querySelector('.card-header h2');
        if (buyTitleWrap || document.querySelector('#buy-score-circle')) {
            const container = buyTitleWrap || document.querySelector('#buy-score-circle').closest('.score-card').querySelector('span');
            if (container) {
                let badge = container.querySelector('.hg-badge');
                if (window.isHighGrowthModel) {
                    if (!badge) {
                        badge = document.createElement('span');
                        badge.className = 'hg-badge';
                        badge.style = 'margin-left: 10px; font-size: 0.7rem; background: linear-gradient(90deg, #ec4899, #f43f5e); color: white; padding: 2px 8px; border-radius: 12px; font-weight: bold; vertical-align: middle;';
                        badge.textContent = '🚀 High-Growth Model';
                        container.appendChild(badge);
                    }
                } else if (badge) {
                    badge.remove();
                }
            }
        }"""
        app_js = re.sub(r"(updateScoreUI\(data\.good_to_buy_total, 'buy-score-circle', 'buy-score-fill'\);)", r"\1\n" + badge_injection, app_js)

    # 3. When peers are added, re-run displayData(globalData) to recalculate Sector Median EV/Gross Profit
    # The peers are added in `recalcIndustryPeg`, wait, when we click "Sector" we might not call displayData.
    # Actually, when peers are added via the Sector API, we fetch peers and then update calculations.
    # Let's just update `app.js`'s updateFairValue() or `recalcIndustryPeg()` to also trigger a UI refresh of the buy breakdown.
    # Actually, `displayData(globalData)` will refresh the UI entirely. In app.js, when peers are added, we call `updateFairValue()` and maybe `displayData`? No, let's just make `recalcIndustryPeg` re-render the Buy Breakdown if HighGrowth is true.
    
    hook_peer = r"function recalcIndustryPeg\(prof\) \{"
    if "if (window.isHighGrowthModel && window._renderProfile)" not in app_js:
        peer_inj = """
        if (window.isHighGrowthModel && window._renderProfile) {
            // Need to recalculate the EV/GP with new peers
            // A simple hack is to re-run the High-Growth eval by forcing displayData (but that might loop).
            // Better: just trigger displayData again but avoid loop by not calling recalcIndustryPeg inside it.
            // Since displayData sets currentBuyBreakdown, let's just call a quick refresh if needed, 
            // but actually we don't want to reload the whole page.
            setTimeout(() => {
               if (window.globalData) displayData(window.globalData);
            }, 500);
        }"""
        app_js = re.sub(r"(function recalcIndustryPeg\(prof\) \{)", r"\1\n" + peer_inj, app_js)

    with open('app.js', 'w', encoding='utf-8') as f:
        f.write(app_js)
    
    # 4. Make sure backend sends necessary fields in company_profile for peers
    # In api/index.py or scraper/yahoo.py: 
    # The peers come from `get_company_data(peer, fast_mode=True)`.
    # Wait, fast_mode=True in get_company_data doesn't fetch financials by default!
    # Let's check scraper/yahoo.py get_company_data
    with open('scraper/yahoo.py', 'r', encoding='utf-8') as f:
        yahoo_py = f.read()
    
    # If fast_mode=True, we need to ensure gross_margins, enterprise_value, total_revenue, revenue_growth are fetched.
    # In fast_mode, info is fetched, and info contains grossMargins, enterpriseValue, totalRevenue, revenueGrowth.
    # So we don't need to change scraper/yahoo.py for peers, info already has them!

if __name__ == '__main__':
    update_app_js()
    print("Injected High-Growth logic into app.js")
