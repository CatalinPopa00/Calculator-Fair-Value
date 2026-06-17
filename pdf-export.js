document.addEventListener('DOMContentLoaded', () => {
    const exportBtn = document.getElementById('export-pdf-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            if (!window.globalData || !window.globalData.ticker) {
                alert('Te rog sÄƒ cauÈ›i o companie mai Ã®ntÃ¢i.');
                return;
            }

            if (typeof html2canvas === 'undefined' || typeof window.jspdf === 'undefined') {
                alert('PDF libraries not fully loaded yet. Please try again in a moment.');
                return;
            }

            const jsPDF = window.jspdf.jsPDF;
            console.log("PDF export process started...");

            const btnOriginalHtml = exportBtn.innerHTML;
            exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> GENERATING...';
            exportBtn.disabled = true;

            const originalScrollY = window.scrollY;

            try {
                const d = window.globalData || {};
                const p = d.company_profile || {};
                const q = d.quote || {};

                const priceVal = d.current_price || q.price || p.price;
                const price = priceVal ? priceVal.toFixed(2) : 'N/A';
                const mktCapRaw = p.mktCap || q.marketCap || d.market_cap || p.marketCap || p.market_cap;
                const mktCap = mktCapRaw ? (mktCapRaw / 1e9).toFixed(2) + 'B' : 'N/A';
                const ind = p.industry || 'N/A';
                const name = p.companyName || d.ticker || 'Company';
                const ticker = d.ticker || 'N/A';
                let logoUrl = p.logo;
                if (!logoUrl && d.website) {
                    let domain = d.website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
                    if (domain) {
                        logoUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent('https://www.google.com/s2/favicons?domain=' + domain + '&sz=128')}`;
                    }
                }
                const logoHtml = logoUrl ? `<img src="${logoUrl}" style="width: 42px; height: 42px; border-radius: 50%; object-fit: contain; background: white; padding: 4px;" crossorigin="anonymous">` : `<div style="width: 42px; height: 42px; border-radius: 50%; background: var(--primary); display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px;">${ticker.charAt(0)}</div>`;

                const scenarioBtns = Array.from(document.querySelectorAll('.scenario-btn:not(.custom-scenarios-btn)'));
                const activeBtn = document.querySelector('.scenario-btn.active:not(.custom-scenarios-btn)');
                if (scenarioBtns.length > 0) {
                    scenarioBtns.forEach(btn => { if (btn && btn.click) btn.click(); });
                    if (activeBtn && activeBtn.click) activeBtn.click();
                }

                const formatFv = (val) => {
                    if (val == null) return 'N/A';
                    if (typeof val === 'number') return '$' + val.toFixed(2);
                    if (val && typeof val === 'object' && val.value != null) return '$' + val.value.toFixed(2);
                    if (typeof val === 'string') {
                        const parsed = parseFloat(val.replace(/[^0-9.-]+/g,""));
                        if (!isNaN(parsed)) return '$' + parsed.toFixed(2);
                    }
                    return 'N/A';
                };

                const scenarioFvs = window._scenarioFvData || {};
                const fallbackFvs = (d.scoring_results) ? d.scoring_results : {};

                const baseVal = formatFv(scenarioFvs.base ?? fallbackFvs.base?.fair_value);
                const bearVal = formatFv(scenarioFvs.bear ?? fallbackFvs.bear?.fair_value);
                const bullVal = formatFv(scenarioFvs.bull ?? fallbackFvs.bull?.fair_value);

                const weights = window.customWeights || { dcf: 25, relative: 25, lynch: 25, peg: 25 };
                
                const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : '';
                
                // Extract SWOT from raw text to ensure it's captured even if the tab wasn't opened
                let strengthsText = '<p style="color: rgba(255,255,255,0.5); font-size: 0.8rem; font-style:italic;">Not available.</p>';
                let risksText = '<p style="color: rgba(255,255,255,0.5); font-size: 0.8rem; font-style:italic;">Not available.</p>';
                let watchoutsText = '<p style="color: rgba(255,255,255,0.5); font-size: 0.8rem; font-style:italic;">Not available.</p>';

                if (d.company_overview_synthesis) {
                    const parts = d.company_overview_synthesis.split(/\*\*(EXECUTIVE SUMMARY|SINTEZA EXECUTIVA|STRATEGIC STRENGTHS|PUNCTE FORTE STRATEGICE|VULNERABILITIES \& RISKS|VULNERABILITÄ‚ÈšI È˜I RISCURI|EARNINGS WATCHOUTS|LATEST MARKET INTELLIGENCE|ULTIMELE INFORMAÈšII DE PIAÈšÄ‚)\*\*/i);
                    let strengths = [];
                    let risks = [];
                    let watchouts = [];

                    for (let i = 1; i < parts.length; i += 2) {
                        const title = parts[i].trim().toUpperCase();
                        const content = parts[i + 1] ? parts[i + 1].trim() : "";
                        
                        if (title === "STRATEGIC STRENGTHS" || title === "PUNCTE FORTE STRATEGICE") {
                            strengths = content.split('\n').map(line => line.replace(/^[-*]\s*/, '').trim()).filter(Boolean);
                        } else if (title === "VULNERABILITIES & RISKS" || title === "VULNERABILITÄ‚ÈšI È˜I RISCURI") {
                            risks = content.split('\n').map(line => line.replace(/^[-*]\s*/, '').trim()).filter(Boolean);
                        } else if (title === "EARNINGS WATCHOUTS" || title === "LATEST MARKET INTELLIGENCE" || title === "ULTIMELE INFORMAÈšII DE PIAÈšÄ‚") {
                            watchouts = content.split('\n').map(line => line.replace(/^[-*]\s*/, '').trim()).filter(Boolean);
                        }
                    }

                    if (strengths.length > 0) {
                        strengthsText = '<div style="display:flex; flex-direction:column; gap:12px; margin-top: 15px;">' + strengths.map(l => `<div style="line-height: 1.5; color: #f8fafc; font-size: 0.95rem;">- ${l}</div>`).join('') + '</div>';
                    }
                    if (risks.length > 0) {
                        risksText = '<div style="display:flex; flex-direction:column; gap:12px; margin-top: 15px;">' + risks.map(l => `<div style="line-height: 1.5; color: #f8fafc; font-size: 0.95rem;">- ${l}</div>`).join('') + '</div>';
                    }
                    if (watchouts.length > 0) {
                        watchoutsText = '<div style="display:flex; flex-direction:column; gap:12px; margin-top: 15px;">' + watchouts.map(l => `<div style="line-height: 1.5; color: #f8fafc; font-size: 0.95rem;">- ${l}</div>`).join('') + '</div>';
                    }
                }
                
                const strengthsHtml = `<h4 style="color: #10b981; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 15px; font-weight: 800;">Strategic Strengths</h4>${strengthsText}`;
                const risksHtml = `<h4 style="color: #ef4444; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 15px; font-weight: 800;">Vulnerabilities & Risks</h4>${risksText}`;
                const keyPointsHtml = `<h4 style="color: #fbbf24; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 15px; font-weight: 800;">Key Points from Latest Reports</h4>${watchoutsText}`;

                // --- PAGE 1 CONTAINER ---
                const container1 = document.createElement('div');
                container1.id = 'pdf-export-temp-container-1';
                container1.style.position = 'absolute';
                container1.style.left = '-9999px';
                container1.style.top = '0';
                container1.style.width = '1200px';
                container1.style.background = '#0f172a';
                container1.style.color = '#f8fafc';
                container1.style.fontFamily = "'Inter', sans-serif";
                container1.style.padding = '40px';
                container1.style.boxSizing = 'border-box';
                container1.style.zIndex = '-1';
                document.body.appendChild(container1);

                // --- PAGE 2 CONTAINER ---
                const container2 = document.createElement('div');
                container2.id = 'pdf-export-temp-container-2';
                container2.style.position = 'absolute';
                container2.style.left = '-9999px';
                container2.style.top = '0';
                container2.style.width = '1200px';
                container2.style.background = '#0f172a';
                container2.style.color = '#f8fafc';
                container2.style.fontFamily = "'Inter', sans-serif";
                container2.style.padding = '40px';
                container2.style.boxSizing = 'border-box';
                container2.style.zIndex = '-1';
                document.body.appendChild(container2);

                const cardStyle = "background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px;";

                container1.innerHTML = `
                    <!-- Top Header Info -->
                    <div style="display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; margin-bottom: 20px;">
                        <div style="display: flex; align-items: center; gap: 15px;">
                            ${logoHtml}
                            <div style="display: flex; flex-direction: column; line-height: 1.1;">
                                <h2 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #f8fafc;">${ticker}</h2>
                                <span style="color: #94a3b8; font-weight: 500; font-size: 1.1rem; margin-top: 4px;">${name}</span>
                            </div>
                        </div>
                        <div style="display: flex; flex-direction: column; align-items: center;">
                            <div style="font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">CURRENT PRICE</div>
                            <div style="font-size: 2.8rem; font-weight: 800; color: #f8fafc; margin-top: 5px;">${price}</div>
                        </div>
                        <div style="text-align: right; color: #94a3b8; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px;">
                            <div style="margin-bottom: 4px;">INDUSTRY</div>
                            <div style="color: #f8fafc; font-weight: 600; font-size: 1.1rem; margin-bottom: 12px;">${ind}</div>
                            <div style="margin-bottom: 4px;">MARKET CAP</div>
                            <div style="color: #f8fafc; font-weight: 600; font-size: 1.1rem;">${mktCap}</div>
                        </div>
                    </div>

                    <!-- Price & Scenarios -->
                    <div style="display: flex; gap: 20px; margin-bottom: 20px; align-items: stretch; justify-content: space-between;">
                        <div style="${cardStyle} flex: 1; text-align: center; padding: 25px;">
                            <h3 style="margin: 0 0 10px 0; color: #ef4444; font-size: 1.2rem;">Bear</h3>
                            <div style="font-size: 2.2rem; font-weight: 800; color: #f8fafc;">${bearVal}</div>
                        </div>
                        <div style="${cardStyle} flex: 1.2; text-align: center; padding: 25px; border: 2px solid #3b82f6;">
                            <h3 style="margin: 0 0 10px 0; color: #3b82f6; font-size: 1.4rem;">Base</h3>
                            <div style="font-size: 2.6rem; font-weight: 800; color: #f8fafc;">${baseVal}</div>
                        </div>
                        <div style="${cardStyle} flex: 1; text-align: center; padding: 25px;">
                            <h3 style="margin: 0 0 10px 0; color: #10b981; font-size: 1.2rem;">Bull</h3>
                            <div style="font-size: 2.2rem; font-weight: 800; color: #f8fafc;">${bullVal}</div>
                        </div>
                    </div>

                    <!-- Middle Grid: Scores & Custom Scenarios -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                        <div id="pdf-scores-container" style="${cardStyle} padding: 25px;"></div>
                        <div style="${cardStyle} padding: 25px;">
                            <h3 style="margin: 0 0 20px 0; font-size: 1.2rem;">Custom Scenarios</h3>
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.95rem; text-align: center;">
                                <thead>
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); color: #94a3b8;">
                                        <th style="text-align: left; padding: 12px 0; font-weight: 500; text-transform: uppercase;">Parameter</th>
                                        <th style="padding: 12px 0; font-weight: 600; color: #ef4444;">Bear</th>
                                        <th style="padding: 12px 0; font-weight: 600; color: #f8fafc;">Base</th>
                                        <th style="padding: 12px 0; font-weight: 600; color: #10b981;">Bull</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">Rev. Growth (%)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-rev-1-3-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-rev-1-3-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-rev-1-3-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">FCF Margin (%)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-fcf-margin-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-fcf-margin-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-fcf-margin-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">WACC (%)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-wacc-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-wacc-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-wacc-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">Exit Multiple (x)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-exit-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-exit-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-exit-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">Perpetual Gr. (%)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-perp-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-perp-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-perp-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">EPS Growth (%)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-eps-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-eps-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-eps-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">Forward P/E 3y</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-pe-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-pe-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">${getVal('cs-pe-bull')}</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Valuation Models -->
                    <div style="display: flex; gap: 15px; margin-bottom: 20px; align-items: stretch;" id="pdf-methods-container">
                        <!-- Clones go here -->
                    </div>

                    <!-- SWOT Insights -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div style="${cardStyle} padding: 25px;">
                            ${strengthsHtml}
                        </div>
                        <div style="${cardStyle} padding: 25px;">
                            ${risksHtml}
                        </div>
                    </div>
                `;

                container2.innerHTML = `
                    <!-- Key Points -->
                    <div style="${cardStyle} padding: 25px; margin-bottom: 20px;">
                        ${keyPointsHtml}
                    </div>
                    </div>
                `;

                
                const appendCloned = (selector, targetContainerId) => {
                    const el = document.querySelector(selector);
                    const target = document.getElementById(targetContainerId);
                    if (el && target) {
                        const clone = el.cloneNode(true);
                        clone.removeAttribute('id');
                        clone.querySelectorAll('[id]').forEach(child => child.removeAttribute('id'));
                        
                        // Strip hover effects or styles if needed
                        clone.style.margin = '0';
                        clone.style.width = '100%';
                        clone.style.maxWidth = '100%';
                        clone.style.boxSizing = 'border-box';
                        
                        if (targetContainerId === 'pdf-methods-container') {
                            clone.style.flex = '1';
                        }
                        
                        target.appendChild(clone);
                        return clone;
                    }
                    return null;
                };

                // Append Scores
                const scoresClone = appendCloned('.row-2-card', 'pdf-scores-container');
                if (scoresClone) {
                    scoresClone.style.background = 'transparent';
                    scoresClone.style.border = 'none';
                    scoresClone.style.boxShadow = 'none';
                    scoresClone.style.padding = '15px';
                    
                    // Remove top strengths & risk factors from the score panel
                    const rightPanel = scoresClone.querySelector('.insights-column') || scoresClone.querySelector('.strengths-risks-container');
                    if (rightPanel) rightPanel.remove();
                    
                    const leftPanel = scoresClone.querySelector('.scores-column');
                    if (leftPanel) {
                        leftPanel.style.width = '100%';
                        leftPanel.style.borderRight = 'none';
                        leftPanel.style.paddingRight = '0';
                        
                        // Enforce full width on all score bars
                        leftPanel.querySelectorAll('.score-bar-wrapper').forEach(wrapper => {
                            wrapper.style.width = '100%';
                            wrapper.style.flex = '1';
                        });
                        leftPanel.querySelectorAll('.score-row').forEach(row => {
                            row.style.display = 'flex';
                            row.style.flexDirection = 'column';
                        });
                        leftPanel.querySelectorAll('.score-display').forEach(disp => {
                            disp.style.display = 'grid';
                            disp.style.gridTemplateColumns = '5rem 1fr 3rem';
                            disp.style.alignItems = 'center';
                            disp.style.gap = '15px';
                            disp.style.width = '100%';
                        });
                        leftPanel.querySelectorAll('.score-circle').forEach(circle => {
                            circle.style.textAlign = 'right';
                        });
                        leftPanel.querySelectorAll('.score-max').forEach(max => {
                            max.style.textAlign = 'left';
                        });
                    }
                }

                // Append Models
                const methodsContainer = document.getElementById('pdf-methods-container');
                
                const m1 = appendCloned('#dcf-card', 'pdf-methods-container');
                const m2 = appendCloned('#relative-card', 'pdf-methods-container');
                const m3 = appendCloned('#peter_lynch-card', 'pdf-methods-container');
                const m4 = appendCloned('#peg-card', 'pdf-methods-container');

                const mWeights = [weights.dcf, weights.relative, weights.lynch, weights.peg];

                [m1, m2, m3, m4].forEach((c, idx) => {
                    if (c) {
                        c.style.background = 'rgba(30, 41, 59, 1)';
                        c.classList.remove('collapsed');
                        c.style.height = '100%';
                        c.style.padding = '15px';
                        c.style.display = 'flex';
                        c.style.flexDirection = 'column';
                        
                        const detailsBtn = c.querySelector('.details-toggle-btn');
                        if (detailsBtn) detailsBtn.remove();
                        const viewDataBtn = c.querySelector('.view-data-btn');
                        if (viewDataBtn) viewDataBtn.remove();

                        const body = c.querySelector('.card-body-collapsible');
                        if (body) {
                            body.style.maxHeight = 'none';
                            body.style.opacity = '1';
                            body.style.display = 'flex';
                            body.style.flexDirection = 'column';
                            body.style.flex = '1';
                        }

                        // Add Weight Share
                        const shareDiv = document.createElement('div');
                        shareDiv.style.marginTop = 'auto'; // pushes it to the bottom
                        shareDiv.style.paddingTop = '15px';
                        shareDiv.style.textAlign = 'center';
                        shareDiv.style.fontSize = '0.9rem';
                        shareDiv.style.color = '#94a3b8';
                        shareDiv.style.fontWeight = 'bold';
                        shareDiv.innerHTML = `<span style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; color: #f8fafc;">${mWeights[idx]}% SHARE</span>`;
                        c.appendChild(shareDiv);
                    }
                });

                // Generate KPI Charts
                const kpiAuditCache = localStorage.getItem('kpiAudit_' + ticker) || localStorage.getItem('kpiAudit' + ticker);
                if (kpiAuditCache) {
                    try {
                        const kpiData = JSON.parse(kpiAuditCache);
                        if (kpiData && kpiData.kpis && kpiData.kpis.length > 0) {
                            const kpiContainer = document.getElementById('pdf-kpi-container');
                            kpiData.kpis.forEach((kpi, index) => {
                                const chartDiv = document.createElement('div');
                                chartDiv.style.cssText = cardStyle + ' padding: 25px; margin-bottom: 20px; page-break-inside: avoid;';
                                
                                const descDiv = document.createElement('div');
                                descDiv.style.marginBottom = '15px';
                                descDiv.innerHTML = `<h4 style="color: var(--accent); margin: 0 0 5px 0; font-size: 1.1rem;">${kpi.name} <span style="color:#94a3b8; font-size:0.8rem; float:right;">(${index+1}/${kpiData.kpis.length})</span></h4><p style="color:#94a3b8; font-size: 0.85rem; margin:0;">${kpi.description}</p>`;
                                chartDiv.appendChild(descDiv);
                                
                                const canvasWrapper = document.createElement('div');
                                canvasWrapper.style.height = '200px';
                                canvasWrapper.style.position = 'relative';
                                
                                const canvas = document.createElement('canvas');
                                canvasWrapper.appendChild(canvas);
                                chartDiv.appendChild(canvasWrapper);
                                kpiContainer.appendChild(chartDiv);

                                // Render chart
                                const periods = kpi.historical_data.map(d => d.period);
                                const values = kpi.historical_data.map(d => parseFloat(d.value) || 0);

                                new Chart(canvas.getContext('2d'), {
                                    type: 'bar',
                                    data: {
                                        labels: periods,
                                        datasets: [{
                                            label: kpi.name,
                                            data: values,
                                            backgroundColor: '#0ea5e9',
                                            borderRadius: 4
                                        }]
                                    },
                                    options: {
                                        responsive: true,
                                        maintainAspectRatio: false,
                                        plugins: { legend: { display: false } },
                                        scales: {
                                            y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: 'rgba(255, 255, 255, 0.5)' } },
                                            x: { grid: { display: false }, ticks: { color: 'rgba(255, 255, 255, 0.5)' } }
                                        },
                                        animation: false // Disable animation for immediate render
                                    }
                                });
                            });
                        }
                    } catch (e) {
                        console.error('Error rendering KPI charts for PDF:', e);
                    }
                } else {
                    document.getElementById('pdf-kpi-container').innerHTML = '<div style="color: #94a3b8; padding: 20px;"><em>AI Business Pulse Audit data not found. Please run the AI Audit in the interface before exporting the PDF to include it here.</em></div>';
                }

                window.scrollTo(0, 0);

                // Wait for layout/charts to render
                await new Promise(r => setTimeout(r, 800));

                const canvas1 = await html2canvas(container1, {
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    scrollY: 0,
                    scrollX: 0,
                    width: 1200,
                    windowWidth: 1200,
                    backgroundColor: '#0f172a'
                });

                const canvas2 = await html2canvas(container2, {
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    scrollY: 0,
                    scrollX: 0,
                    width: 1200,
                    windowWidth: 1200,
                    backgroundColor: '#0f172a'
                });

                const pdf = new jsPDF('p', 'mm', 'a4');
                pdf.setFillColor(15, 23, 42); // match #0f172a

                const pdfWidth = 210;
                let pdfHeight = 297;

                // --- Page 1 ---
                let imgData1 = canvas1.toDataURL('image/jpeg', 0.95);
                let imgProps1 = pdf.getImageProperties(imgData1);
                let ratio1 = imgProps1.width / pdfWidth;
                let imgHeightInMm1 = imgProps1.height / ratio1;
                
                pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                pdf.addImage(imgData1, 'JPEG', 0, 0, pdfWidth, imgHeightInMm1);

                // --- Page 2 ---
                pdf.addPage();
                let imgData2 = canvas2.toDataURL('image/jpeg', 0.95);
                let imgProps2 = pdf.getImageProperties(imgData2);
                let ratio2 = imgProps2.width / pdfWidth;
                let imgHeightInMm2 = imgProps2.height / ratio2;

                let heightLeft = imgHeightInMm2;
                let position = 0;

                pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                pdf.addImage(imgData2, 'JPEG', 0, position, pdfWidth, imgHeightInMm2);
                heightLeft -= pdfHeight;

                while (heightLeft > 0) {
                    position -= pdfHeight;
                    pdf.addPage();
                    pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                    pdf.addImage(imgData2, 'JPEG', 0, position, pdfWidth, imgHeightInMm2);
                    heightLeft -= pdfHeight;
                }

                pdf.save(`${ticker}_Fair_Value_Report.pdf`);

            } catch (e) {
                console.error("PDF Export Error:", e);
                alert("Failed to export PDF.");
            } finally {
                const c1 = document.getElementById('pdf-export-temp-container-1');
                if (c1) c1.remove();
                const c2 = document.getElementById('pdf-export-temp-container-2');
                if (c2) c2.remove();

                window.scrollTo(0, originalScrollY);
                exportBtn.innerHTML = btnOriginalHtml;
                exportBtn.disabled = false;
            }
        });
    }
});
