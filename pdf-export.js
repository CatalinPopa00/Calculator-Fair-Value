document.addEventListener('DOMContentLoaded', () => {
    const exportBtn = document.getElementById('export-pdf-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            if (!window.globalData || !window.globalData.ticker) {
                alert('Te rog să cauți o companie mai întâi.');
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
                const logoHtml = p.logo ? `<img src="${p.logo}" style="width: 42px; height: 42px; border-radius: 50%; object-fit: contain; background: white; padding: 4px;" crossorigin="anonymous">` : `<div style="width: 42px; height: 42px; border-radius: 50%; background: var(--primary); display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px;">${ticker.charAt(0)}</div>`;

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
                    const lines = d.company_overview_synthesis.split('\n');
                    let currentSection = '';
                    let strengths = [];
                    let risks = [];
                    let watchouts = [];

                    for (let line of lines) {
                        line = line.trim();
                        if (!line) continue;
                        
                        const upperLine = line.toUpperCase();
                        if (upperLine.includes('STRATEGIC STRENGTHS') || upperLine.includes('PUNCTE FORTE STRATEGICE')) {
                            currentSection = 'strengths';
                            continue;
                        } else if (upperLine.includes('VULNERABILITIES & RISKS') || upperLine.includes('VULNERABILITĂȚI ȘI RISCURI')) {
                            currentSection = 'risks';
                            continue;
                        } else if (upperLine.includes('LATEST MARKET INTELLIGENCE') || upperLine.includes('ULTIMELE INFORMAȚII DE PIAȚĂ') || upperLine.includes('KEY POINTS')) {
                            currentSection = 'watchouts';
                            continue;
                        } else if (upperLine.includes('VALUATION SYNOPSIS') || upperLine.includes('SINOPSIS DE EVALUARE')) {
                            currentSection = 'valuation';
                            continue;
                        }

                        if (line.startsWith('-') || line.startsWith('*')) {
                            const val = line.replace(/^[-*]\s*/, '');
                            if (currentSection === 'strengths') strengths.push(val);
                            else if (currentSection === 'risks') risks.push(val);
                            else if (currentSection === 'watchouts') watchouts.push(val);
                        }
                    }

                    if (strengths.length > 0) {
                        strengthsText = '<ul style="margin:0; padding-left: 20px;">' + strengths.map(l => `<li style="margin-bottom:12px; line-height: 1.4; color: #f8fafc;">${l}</li>`).join('') + '</ul>';
                    }
                    if (risks.length > 0) {
                        risksText = '<ul style="margin:0; padding-left: 20px;">' + risks.map(l => `<li style="margin-bottom:12px; line-height: 1.4; color: #f8fafc;">${l}</li>`).join('') + '</ul>';
                    }
                    if (watchouts.length > 0) {
                        watchoutsText = '<ul style="margin:0; padding-left: 20px;">' + watchouts.map(l => `<li style="margin-bottom:12px; line-height: 1.4; color: #f8fafc;">${l}</li>`).join('') + '</ul>';
                    }
                }
                
                const strengthsHtml = `<h4 style="color: #10b981; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 15px; font-weight: 800;">Strategic Strengths</h4>${strengthsText}`;
                const risksHtml = `<h4 style="color: #ef4444; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 15px; font-weight: 800;">Vulnerabilities & Risks</h4>${risksText}`;
                const keyPointsHtml = `<h4 style="color: #fbbf24; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 15px; font-weight: 800;">Key Points from Latest Reports</h4>${watchoutsText}`;

                const container = document.createElement('div');
                container.id = 'pdf-export-temp-container';
                container.style.width = '1200px';
                container.style.background = '#0f172a';
                container.style.color = '#f8fafc';
                container.style.fontFamily = "'Outfit', sans-serif";
                container.style.padding = '40px';
                container.style.boxSizing = 'border-box';
                container.style.position = 'absolute';
                container.style.top = '0';
                container.style.left = '0';
                container.style.zIndex = '-9999';
                container.style.display = 'block';

                const cardStyle = "background: rgba(30, 41, 59, 1); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);";

                // Layout Building
                container.innerHTML = `
                    <!-- Top Header Info -->
                    <div style="display: flex; justify-content: flex-end; align-items: flex-end; margin-bottom: 10px;">
                        <div style="text-align: right; color: #94a3b8; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px;">
                            <div style="margin-bottom: 4px;">INDUSTRY</div>
                            <div style="color: #f8fafc; font-weight: 600; font-size: 1.1rem; margin-bottom: 12px;">${ind}</div>
                            <div style="margin-bottom: 4px;">MARKET CAP</div>
                            <div style="color: #f8fafc; font-weight: 600; font-size: 1.1rem;">$${mktCap}</div>
                        </div>
                    </div>

                    <!-- Price & Scenarios -->
                    <div style="display: flex; gap: 20px; margin-bottom: 20px; align-items: stretch;">
                        <div style="${cardStyle} padding: 25px; min-width: 250px; display: flex; flex-direction: column; justify-content: center;">
                            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 15px;">
                                ${logoHtml}
                                <div style="display: flex; flex-direction: column;">
                                    <div style="font-size: 1.6rem; font-weight: 800; line-height: 1.1;">${name}</div>
                                    <div style="color: #94a3b8; font-weight: 500; font-size: 1rem;">${ticker}</div>
                                </div>
                            </div>
                            <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">CURRENT PRICE</div>
                            <div style="font-size: 2.8rem; font-weight: 800;">$${price}</div>
                        </div>
                        <div style="${cardStyle} flex: 1; display: flex; padding: 20px; justify-content: space-between; align-items: center;">
                            <div style="text-align: center; flex: 1;">
                                <h3 style="margin: 0 0 10px 0; color: #ef4444; font-size: 1.2rem;">Bear</h3>
                                <div style="font-size: 1.8rem; font-weight: 800;">${bearVal}</div>
                            </div>
                            <div style="width: 1px; background: rgba(255,255,255,0.1); height: 80%;"></div>
                            <div style="text-align: center; flex: 1.2;">
                                <h3 style="margin: 0 0 10px 0; color: #3b82f6; font-size: 1.4rem;">Base</h3>
                                <div style="font-size: 2.2rem; font-weight: 800; color: #3b82f6;">${baseVal}</div>
                            </div>
                            <div style="width: 1px; background: rgba(255,255,255,0.1); height: 80%;"></div>
                            <div style="text-align: center; flex: 1;">
                                <h3 style="margin: 0 0 10px 0; color: #10b981; font-size: 1.2rem;">Bull</h3>
                                <div style="font-size: 1.8rem; font-weight: 800;">${bullVal}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Middle Grid: Scores & Custom Scenarios -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                        <div id="pdf-scores-container" style="${cardStyle}"></div>
                        <div style="${cardStyle} padding: 20px;">
                            <h3 style="margin: 0 0 20px 0; font-size: 1.2rem;">Custom Scenarios</h3>
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: center;">
                                <thead>
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); color: #94a3b8;">
                                        <th style="text-align: left; padding: 8px 0; font-weight: 500; text-transform: uppercase;">Parameter</th>
                                        <th style="padding: 8px 0; font-weight: 600; color: #ef4444;">Bear</th>
                                        <th style="padding: 8px 0; font-weight: 600; color: #f8fafc;">Base</th>
                                        <th style="padding: 8px 0; font-weight: 600; color: #10b981;">Bull</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr><td style="text-align:left; padding:8px 0; color: #94a3b8;">Rev. Growth (%)</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-rev-1-3-bear')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-rev-1-3-base')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-rev-1-3-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:8px 0; color: #94a3b8;">FCF Margin (%)</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-fcf-margin-bear')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-fcf-margin-base')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-fcf-margin-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:8px 0; color: #94a3b8;">WACC (%)</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-wacc-bear')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-wacc-base')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-wacc-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:8px 0; color: #94a3b8;">Exit Multiple (x)</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-exit-bear')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-exit-base')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-exit-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:8px 0; color: #94a3b8;">Perpetual Gr. (%)</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-perp-bear')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-perp-base')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-perp-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:8px 0; color: #94a3b8;">EPS Growth (%)</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-eps-bear')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-eps-base')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-eps-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:8px 0; color: #94a3b8;">Forward P/E 3y</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-pe-bear')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-pe-base')}</td><td style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);">${getVal('cs-pe-bull')}</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Valuation Models -->
                    <div style="display: flex; gap: 10px; margin-bottom: 20px; align-items: stretch;" id="pdf-methods-container">
                        <!-- Clones go here -->
                        <div id="pdf-weights-container" style="${cardStyle} flex: 1; padding: 15px; font-size: 0.85rem; display: flex; flex-direction: column; justify-content: center;">
                            <div style="text-align: center; font-weight: 600; margin-bottom: 10px; color: #94a3b8;">Model Weights (%)</div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;"><span>DCF Model</span> <span style="background:rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">${weights.dcf}</span></div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;"><span>Rel Valuation</span> <span style="background:rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">${weights.relative}</span></div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;"><span>Fwd Multiple</span> <span style="background:rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">${weights.lynch}</span></div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;"><span>PEG Valuation</span> <span style="background:rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">${weights.peg}</span></div>
                        </div>
                    </div>

                    <!-- SWOT Insights -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                        <div style="${cardStyle} padding: 20px;">
                            ${strengthsHtml}
                        </div>
                        <div style="${cardStyle} padding: 20px;">
                            ${risksHtml}
                        </div>
                    </div>
                    <div style="${cardStyle} padding: 20px; margin-bottom: 20px;">
                        ${keyPointsHtml}
                    </div>
                    
                    <!-- AI Business Pulse Audit -->
                    <div style="margin-top: 40px; padding-top: 20px; border-top: 2px solid rgba(255,255,255,0.05);" id="pdf-kpi-container">
                        <h2 style="text-align: center; font-size: 1.8rem; margin-bottom: 30px;">✨ AI Business Pulse Audit</h2>
                        <!-- KPI charts will be appended here -->
                    </div>
                `;

                document.body.appendChild(container);

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
                    const rightPanel = scoresClone.querySelector('.scores-right-panel') || scoresClone.querySelector('.strengths-risks-container');
                    if (rightPanel) rightPanel.remove();
                    
                    const leftPanel = scoresClone.querySelector('.scores-column');
                    if (leftPanel) {
                        leftPanel.style.width = '100%';
                        leftPanel.style.borderRight = 'none';
                        leftPanel.style.paddingRight = '0';
                    }
                }

                // Append Models (Left 2, then Weights, then Right 2)
                const methodsContainer = document.getElementById('pdf-methods-container');
                const weightsContainer = document.getElementById('pdf-weights-container');
                
                const m1 = appendCloned('#dcf-card', 'pdf-methods-container');
                const m2 = appendCloned('#relative-card', 'pdf-methods-container');
                methodsContainer.appendChild(weightsContainer); // move weights to middle
                const m3 = appendCloned('#fwd-multiple-card', 'pdf-methods-container');
                const m4 = appendCloned('#peg-card', 'pdf-methods-container');

                [m1, m2, m3, m4].forEach(c => {
                    if (c) {
                        c.style.background = 'rgba(30, 41, 59, 1)';
                        c.classList.remove('collapsed');
                        c.style.height = '100%';
                        c.style.padding = '15px';
                        
                        const detailsBtn = c.querySelector('.details-toggle-btn');
                        if (detailsBtn) detailsBtn.remove();
                        const viewDataBtn = c.querySelector('.view-data-btn');
                        if (viewDataBtn) viewDataBtn.remove();

                        const body = c.querySelector('.card-body-collapsible');
                        if (body) {
                            body.style.maxHeight = 'none';
                            body.style.opacity = '1';
                            body.style.display = 'flex';
                        }
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
                    document.getElementById('pdf-kpi-container').style.display = 'none';
                }

                window.scrollTo(0, 0);

                // Wait for layout/charts to render
                await new Promise(r => setTimeout(r, 800));

                const canvas = await html2canvas(container, {
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    scrollY: 0,
                    scrollX: 0,
                    width: 1200,
                    windowWidth: 1200,
                    backgroundColor: '#0f172a'
                });

                const imgData = canvas.toDataURL('image/jpeg', 0.95);
                const pdf = new jsPDF('p', 'mm', 'a4');
                pdf.setFillColor(15, 23, 42); // match #0f172a

                const pdfWidth = 210;
                const pdfHeight = 297;
                const imgProps = pdf.getImageProperties(imgData);
                const ratio = imgProps.width / pdfWidth;
                const imgHeightInMm = imgProps.height / ratio;

                let heightLeft = imgHeightInMm;
                let position = 0;

                pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                pdf.addImage(imgData, 'JPEG', 0, position, pdfWidth, imgHeightInMm);
                heightLeft -= pdfHeight;

                while (heightLeft > 0) {
                    position -= pdfHeight;
                    pdf.addPage();
                    pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                    pdf.addImage(imgData, 'JPEG', 0, position, pdfWidth, imgHeightInMm);
                    heightLeft -= pdfHeight;
                }

                pdf.save(`${ticker}_Fair_Value_Report.pdf`);

            } catch (e) {
                console.error("PDF Export Error:", e);
                alert("Failed to export PDF.");
            } finally {
                const c = document.getElementById('pdf-export-temp-container');
                if (c) c.remove();

                window.scrollTo(0, originalScrollY);
                exportBtn.innerHTML = btnOriginalHtml;
                exportBtn.disabled = false;
            }
        });
    }
});
