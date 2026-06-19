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
                const name = d.name || p.companyName || p.name || d.ticker || 'Company';
                const ticker = d.ticker || 'N/A';
                
                let logoUrl = '';
                const logoEl = document.getElementById('company-logo');
                if (logoEl && logoEl.src && logoEl.src.startsWith('http') && logoEl.style.display !== 'none') {
                    logoUrl = logoEl.src;
                } else if (p.image || p.logo) {
                    logoUrl = p.image || p.logo;
                }
                
                let base64Logo = null;
                if (logoUrl) {
                    const fetchImageAsBase64 = async (url) => {
                        const blobToBase64 = (blob) => {
                            return new Promise((resolve, reject) => {
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result);
                                reader.onerror = reject;
                                reader.readAsDataURL(blob);
                            });
                        };

                        try {
                            const response = await fetch(url);
                            if (!response.ok) throw new Error('Direct fetch failed');
                            const blob = await response.blob();
                            return await blobToBase64(blob);
                        } catch (err) {
                            console.log('Direct logo fetch failed, trying proxies...', err);
                            const proxies = [
                                `https://wsrv.nl/?url=${encodeURIComponent(url)}`,
                                `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
                                `https://corsproxy.io/?${encodeURIComponent(url)}`
                            ];
                            for (let proxy of proxies) {
                                try {
                                    const pRes = await fetch(proxy);
                                    if (!pRes.ok) continue;
                                    const pBlob = await pRes.blob();
                                    return await blobToBase64(pBlob);
                                } catch (e) {
                                    console.log('Proxy failed: ' + proxy);
                                }
                            }
                            throw new Error('All logo fetch attempts failed');
                        }
                    };

                    try {
                        base64Logo = await fetchImageAsBase64(logoUrl);
                    } catch (e) {
                        console.log('Failed to fetch logo as base64', e);
                    }
                }

                const logoHtml = base64Logo ? `<img src="${base64Logo}" style="width: 42px; height: 42px; border-radius: 50%; object-fit: contain; background: white; padding: 4px;">` : `<div style="width: 42px; height: 42px; border-radius: 50%; background: #3b82f6; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; color: white;">${ticker.charAt(0)}</div>`;

                // Capture current widths of score bars before scenario switch resets them
                const originalWidths = [];
                const row2Card = document.querySelector('.row-2-card');
                if (row2Card) {
                    row2Card.querySelectorAll('.score-bar-fill').forEach(fill => {
                        originalWidths.push(fill.style.width);
                    });
                }

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
                        } else if (title === "EARNINGS WATCHOUTS") {
                            watchouts = content.split('\n').map(line => line.replace(/^[-*]\s*/, '').trim()).filter(Boolean);
                        }
                    }

                    const formatBullet = (text) => {
                        // Converts **"Title"**: description to a block bold title + description
                        return text.replace(/\*\*(?:"|')?(.*?)(?:"|')?\*\*:?\s*/g, '<strong style="color: #ffffff; display: block; margin-bottom: 4px; font-size: 1.05rem;">$1</strong>');
                    };

                    if (strengths.length > 0) {
                        strengthsText = '<div style="display:flex; flex-direction:column; gap:12px; margin-top: 15px;">' + strengths.map(l => `<div style="line-height: 1.5; color: #cbd5e1; font-size: 0.95rem;">- ${formatBullet(l)}</div>`).join('') + '</div>';
                    }
                    if (risks.length > 0) {
                        risksText = '<div style="display:flex; flex-direction:column; gap:12px; margin-top: 15px;">' + risks.map(l => `<div style="line-height: 1.5; color: #cbd5e1; font-size: 0.95rem;">- ${formatBullet(l)}</div>`).join('') + '</div>';
                    }
                    if (watchouts.length > 0) {
                        watchoutsText = '<div style="display:flex; flex-direction:column; gap:12px; margin-top: 15px;">' + watchouts.map(l => `<div style="line-height: 1.5; color: #cbd5e1; font-size: 0.95rem;">- ${formatBullet(l)}</div>`).join('') + '</div>';
                    }
                }
                
                const strengthsHtml = `<h4 style="color: #10b981; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Strategic Strengths</h4>${strengthsText}`;
                const risksHtml = `<h4 style="color: #ef4444; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Vulnerabilities & Risks</h4>${risksText}`;
                const keyPointsHtml = `<h4 style="color: #fbbf24; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Key Points from Latest Reports</h4>${watchoutsText}`;

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
                container2.style.zIndex = '-1';
                container2.style.background = '#0f172a';
                container2.style.color = '#f8fafc';
                container2.style.fontFamily = "'Inter', sans-serif";
                container2.style.padding = '40px';
                container2.style.boxSizing = 'border-box';
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
                    <div style="display: flex; gap: 15px; margin-bottom: 15px; align-items: stretch; justify-content: space-between;">
                        <div style="${cardStyle} flex: 1; text-align: center; padding: 15px;">
                            <h3 style="margin: 0 0 10px 0; color: #ef4444; font-size: 1.2rem;">Bear</h3>
                            <div style="font-size: 2.2rem; font-weight: 800; color: #f8fafc;">${bearVal}</div>
                        </div>
                        <div style="${cardStyle} flex: 1.2; text-align: center; padding: 15px; border: 2px solid #3b82f6;">
                            <h3 style="margin: 0 0 10px 0; color: #3b82f6; font-size: 1.4rem;">Base</h3>
                            <div style="font-size: 2.6rem; font-weight: 800; color: #f8fafc;">${baseVal}</div>
                        </div>
                        <div style="${cardStyle} flex: 1; text-align: center; padding: 15px;">
                            <h3 style="margin: 0 0 10px 0; color: #10b981; font-size: 1.2rem;">Bull</h3>
                            <div style="font-size: 2.2rem; font-weight: 800; color: #f8fafc;">${bullVal}</div>
                        </div>
                    </div>

                    <!-- Middle Grid: Scores & Custom Scenarios -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                        <div id="pdf-scores-container" style="${cardStyle} padding: 15px;"></div>
                        <div style="${cardStyle} padding: 15px;">
                            <h3 style="margin: 0 0 15px 0; font-size: 1.2rem;">Custom Scenarios</h3>
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: center;">
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
                    <div style="display: flex; gap: 15px; margin-bottom: 15px; align-items: stretch;" id="pdf-methods-container">
                        <!-- Clones go here -->
                    </div>

                    <!-- SWOT Insights -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                        <div style="${cardStyle} padding: 15px;">
                            ${strengthsHtml}
                        </div>
                        <div style="${cardStyle} padding: 15px;">
                            ${risksHtml}
                        </div>
                    </div>

                    <!-- Key Points -->
                    <div style="${cardStyle} padding: 15px; margin-bottom: 10px;">
                        ${keyPointsHtml}
                    </div>
                `;

                container2.innerHTML = `
                    <!-- AI Business Pulse Audit -->
                    <div id="pdf-export-audit-title" style="display: none;">
                        <h2 style="font-size: 1.8rem; font-weight: 800; color: #f8fafc; border-bottom: 2px solid rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 20px;">AI Business Pulse Audit</h2>
                    </div>
                    <div id="pdf-export-kpi-container" style="display: none; flex-direction: column; gap: 20px;"></div>
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
                    scoresClone.querySelectorAll('.score-bar-fill').forEach((fill, index) => {
                        if (originalWidths[index] !== undefined) {
                            fill.style.width = originalWidths[index];
                            fill.style.transition = 'none'; // Ensure html2canvas captures it immediately
                        }
                    });
                    
                    scoresClone.style.background = 'transparent';
                    scoresClone.style.border = 'none';
                    scoresClone.style.boxShadow = 'none';
                    scoresClone.style.padding = '15px';
                    
                    // Remove "i" emoji button and info icons
                    scoresClone.querySelectorAll('button, .info-icon').forEach(el => el.remove());
                    
                    // Fix grid so it occupies full width instead of 50%
                    const row2Grid = scoresClone.querySelector('.row-2-grid');
                    if (row2Grid) {
                        row2Grid.style.display = 'block';
                    }

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
                        c.style.background = '#1e293b';
                        c.classList.remove('glass-card', 'collapsed');
                        c.style.border = '1px solid rgba(255,255,255,0.05)';
                        c.style.boxShadow = 'none';
                        c.style.borderRadius = '12px';
                        c.style.height = 'auto';
                        c.style.padding = '15px';
                        c.style.display = 'flex';
                        c.style.flexDirection = 'column';
                        c.style.justifyContent = 'flex-start';

                        // Remove input groups and unnecessary elements
                        c.querySelectorAll('.card-inputs, .info-icon, .toggle-container, button').forEach(el => el.remove());
                        
                        // Shrink fixed heights
                        c.querySelectorAll('.card-metrics').forEach(m => { 
                            m.style.minHeight = 'auto'; 
                            m.style.marginBottom = '5px';
                        });

                        const footer = c.querySelector('.card-footer');
                        if (footer) {
                            footer.style.marginTop = '10px';
                        }
                        
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
                        shareDiv.style.marginTop = '15px'; // pushes it to the bottom without stretching
                        shareDiv.style.paddingTop = '10px';
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
                            const kpiContainer = container2.querySelector('#pdf-export-kpi-container');
                            const auditTitle = container2.querySelector('#pdf-export-audit-title');
                            if (kpiContainer && auditTitle) {
                                auditTitle.style.display = 'block';
                                kpiContainer.style.display = 'flex';

                                let currentRow = null;
                                kpiData.kpis.forEach((kpi, index) => {
                                    if (index % 2 === 0) {
                                        currentRow = document.createElement('div');
                                        currentRow.className = 'pdf-kpi-row';
                                        currentRow.style.display = 'grid';
                                        currentRow.style.gridTemplateColumns = '1fr 1fr';
                                        currentRow.style.gap = '20px';
                                        kpiContainer.appendChild(currentRow);
                                    }

                                    const chartDiv = document.createElement('div');
                                    chartDiv.style.cssText = cardStyle + ' padding: 25px; page-break-inside: avoid; background: #1e293b;';
                                    
                                    const descDiv = document.createElement('div');
                                    descDiv.style.marginBottom = '15px';
                                    descDiv.innerHTML = `<h4 style="color: #3b82f6; margin: 0 0 5px 0; font-size: 1.1rem;">${kpi.name} <span style="color:#94a3b8; font-size:0.8rem; float:right;">(${index+1}/${kpiData.kpis.length})</span></h4><p style="color:#94a3b8; font-size: 0.85rem; margin:0;">${kpi.description}</p>`;
                                    chartDiv.appendChild(descDiv);
                                    
                                    const canvasWrapper = document.createElement('div');
                                    canvasWrapper.style.height = '200px';
                                    canvasWrapper.style.position = 'relative';
                                    
                                    const canvas = document.createElement('canvas');
                                    canvasWrapper.appendChild(canvas);
                                    chartDiv.appendChild(canvasWrapper);
                                    currentRow.appendChild(chartDiv);

                                    // Render chart
                                    const vals = kpi.values || kpi.history || kpi.data || {};
                                    const periods = Object.keys(vals).sort();

                                    const parseKpiValue = (val) => {
                                        if (typeof val === 'number') return val;
                                        if (!val || val === '--' || val === 'N/A') return null;

                                        const valStr = String(val).replace(/,/g, '').trim();
                                        const match = valStr.match(/^.*?(-?\d+(?:\.\d+)?)\s*(T|B|M|K|TRILLION|BILLION|MILLION|THOUSAND)?\b/i);
                                        if (match) {
                                            let num = parseFloat(match[1]);
                                            const suffix = (match[2] || '').toUpperCase();
                                            if (suffix === 'T' || suffix === 'TRILLION') num *= 1000000000000;
                                            else if (suffix === 'B' || suffix === 'BILLION') num *= 1000000000;
                                            else if (suffix === 'M' || suffix === 'MILLION') num *= 1000000;
                                            else if (suffix === 'K' || suffix === 'THOUSAND') num *= 1000;

                                            // Fallback logic for text string containing "No specific numerical values"
                                            if (valStr.toLowerCase().includes("no specific numerical values") || valStr.toLowerCase().includes("not reported")) {
                                                 return null;
                                            }
                                            return num;
                                        }
                                        return null;
                                    };

                                    const chartData = periods.map(p => parseKpiValue(vals[p]));
                                    const formattedTooltips = periods.map(p => vals[p]);

                                    // Check if we have valid plottable data
                                    const hasValidData = chartData.some(v => v !== null && v !== undefined && !isNaN(v));

                                    if (!hasValidData || periods.length === 0) {
                                        canvasWrapper.style.display = 'none';
                                        const noDataMsg = document.createElement('div');
                                        noDataMsg.style.display = 'flex';
                                        noDataMsg.style.flexDirection = 'column';
                                        noDataMsg.style.alignItems = 'center';
                                        noDataMsg.style.justifyContent = 'center';
                                        noDataMsg.style.color = 'rgba(255,255,255,0.5)';
                                        noDataMsg.style.textAlign = 'center';
                                        noDataMsg.style.padding = '20px';
                                        const firstMention = Object.values(vals)[0] || 'N/A';
                                        noDataMsg.innerHTML = `<span style="font-size: 1.5rem; margin-bottom: 10px;">📉</span><i>Numerical history could not be plotted for this KPI.</i><br><span style="margin-top: 10px; font-size: 0.9rem;">Most recent mention: <strong style="color:var(--accent);">${firstMention}</strong></span>`;
                                        chartDiv.appendChild(noDataMsg);
                                        return;
                                    }

                                    new Chart(canvas.getContext('2d'), {
                                        type: 'bar',
                                        data: {
                                            labels: periods,
                                            datasets: [{
                                                label: kpi.name,
                                                data: chartData,
                                                backgroundColor: 'rgba(0, 210, 255, 0.4)',
                                                borderColor: 'rgba(0, 210, 255, 1)',
                                                borderWidth: 1,
                                                borderRadius: 4
                                            }]
                                        },
                                        options: {
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            plugins: {
                                                legend: { display: false },
                                                tooltip: {
                                                    callbacks: {
                                                        label: function(context) {
                                                            return ' ' + formattedTooltips[context.dataIndex];
                                                        }
                                                    }
                                                }
                                            },
                                            scales: {
                                                y: {
                                                    beginAtZero: true,
                                                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                                                    ticks: {
                                                        color: 'rgba(255, 255, 255, 0.5)',
                                                        callback: function(value) {
                                                            if (Math.abs(value) >= 1000000000000) return (value / 1000000000000).toFixed(1) + 'T';
                                                            if (Math.abs(value) >= 1000000000) return (value / 1000000000).toFixed(1) + 'B';
                                                            if (Math.abs(value) >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                                                            if (Math.abs(value) >= 1000) return (value / 1000).toFixed(1) + 'K';
                                                            return value;
                                                        }
                                                    }
                                                },
                                                x: { grid: { display: false }, ticks: { color: 'rgba(255, 255, 255, 0.5)' } }
                                            },
                                            animation: false // Disable animation for immediate render
                                        }
                                    });
                                });
                            }
                        }
                    } catch (e) {
                        console.error('Error rendering KPI charts for PDF:', e);
                    }
                }

                window.scrollTo(0, 0);

                // Wait for layout/charts to render
                await new Promise(r => setTimeout(r, 3500));

                const canvas1 = await html2canvas(container1, {
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    scrollY: 0,
                    scrollX: 0,
                    width: 1200,
                    windowWidth: 1200,
                    height: container1.scrollHeight,
                    windowHeight: container1.scrollHeight,
                    backgroundColor: '#0f172a'
                });

                const pdf = new jsPDF('p', 'mm', 'a4');
                pdf.setFillColor(15, 23, 42); // match #0f172a
                const pdfWidth = 210;
                const pdfHeight = 297;
                let currentY = 0;

                // --- Page 1 ---
                let imgData1 = canvas1.toDataURL('image/jpeg', 0.95);
                let imgProps1 = pdf.getImageProperties(imgData1);
                let ratio1 = imgProps1.width / pdfWidth;
                let imgHeightInMm1 = imgProps1.height / ratio1;
                
                pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                pdf.addImage(imgData1, 'JPEG', 0, currentY, pdfWidth, imgHeightInMm1);

                // --- Page 2 and beyond (Iterating through KPI charts to prevent cutting) ---

                // Get the KPI container and title
                const titleSection = container2.querySelector('#pdf-export-audit-title');
                const kpiContainer = container2.querySelector('#pdf-export-kpi-container');

                // Keep track of current height used on the current page
                let currentHeightUsed = 0;

                if (titleSection || (kpiContainer && kpiContainer.children.length > 0)) {
                    pdf.addPage();
                    pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');

                    if (titleSection) {
                         const titleCanvas = await html2canvas(titleSection, {
                            scale: 2,
                            useCORS: true,
                            logging: false,
                            backgroundColor: '#0f172a'
                         });
                         let titleImg = titleCanvas.toDataURL('image/jpeg', 0.95);
                         let titleProps = pdf.getImageProperties(titleImg);
                         let titleRatio = titleProps.width / pdfWidth;
                         let titleH = titleProps.height / titleRatio;

                         pdf.addImage(titleImg, 'JPEG', 0, currentHeightUsed, pdfWidth, titleH);
                         currentHeightUsed += titleH + 5; // 5mm gap
                    }

                    if (kpiContainer) {
                        const charts = Array.from(kpiContainer.children);
                        for (let i = 0; i < charts.length; i++) {
                            const chartCard = charts[i];
                            const chartCanvas = await html2canvas(chartCard, {
                                scale: 2,
                                useCORS: true,
                                logging: false,
                                backgroundColor: '#1e293b' // match card background
                            });

                            let chartImg = chartCanvas.toDataURL('image/jpeg', 0.95);
                            let chartProps = pdf.getImageProperties(chartImg);
                            let chartRatio = (chartProps.width + 40) / pdfWidth; // slightly pad the width ratio to leave margins
                            let chartW = chartProps.width / chartRatio;
                            let chartH = chartProps.height / chartRatio;

                            // Center horizontally roughly by adding 10mm margin
                            let marginX = (pdfWidth - chartW) / 2;

                            // Check if adding this chart will overflow the page
                            if (currentHeightUsed + chartH > pdfHeight - 10) { // 10mm bottom margin
                                pdf.addPage();
                                pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                                currentHeightUsed = 10; // Start with 10mm top margin on new page
                            }

                            pdf.addImage(chartImg, 'JPEG', marginX, currentHeightUsed, chartW, chartH);
                            currentHeightUsed += chartH + 10; // 10mm gap between cards
                        }
                    }
                }

                // --- Subsequent Pages (Iterative) ---
                // We no longer need to manually iterate Key Points or audit sections because
                // Key Points is in container1, and KPIs are handled by the block above.
                // We keep the saving logic below.

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
