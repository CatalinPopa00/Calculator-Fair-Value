document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('search-btn');
    const tickerInput = document.getElementById('ticker-input');

    // Dashboard elements
    const dashboard = document.getElementById('dashboard');
    const loadingState = document.getElementById('loading-state');

    // Modal elements (dynamically injected later via injectDataModal / injectScoreModal)

    // Global selected lynch method
    const lynchMethodSelect = document.getElementById('lynch-method-select');
    let selectedLynchMethod = 'pe20'; // default

    // Watchlist elements
    const navWatchlistBtn = document.getElementById('nav-watchlist-btn');
    const watchlistView = document.getElementById('watchlist-view');
    const watchlistGrid = document.getElementById('watchlist-grid');
    const emptyWatchlistMsg = document.getElementById('empty-watchlist-msg');
    const addToWatchlistBtn = document.getElementById('add-to-watchlist-btn');

    // Autocomplete elements
    const autocompleteList = document.getElementById('autocomplete-list');
    const logoBtn = document.getElementById('logo-btn');

    let currentFormulaData = null;
    let currentTicker = null;
    let currentHealthBreakdown = null;
    let currentBuyBreakdown = null;
    let chartRevFcf = null;
    let chartEpsShares = null;
    let globalData = null; 

    // Custom Weights Logic
    let customWeights = JSON.parse(localStorage.getItem('fairValueWeights')) || { dcf: 25, peg: 25, relative: 25, lynch: 25 };

    // Watchlist State 
    let watchlist = JSON.parse(localStorage.getItem('fairValueWatchlist')) || [];
    
    // Sync watchlist from server on init
    fetch('/api/watchlist').then(r => r.json()).then(data => {
        if (Array.isArray(data)) {
            watchlist = data;
            localStorage.setItem('fairValueWatchlist', JSON.stringify(watchlist));
        }
    }).catch(err => console.error('Watchlist initial sync error:', err));

    // Overrides State (loaded from server on init)
    let cachedOverrides = {};
    let overrideSaveTimer = null;

    // Load overrides from server on startup
    fetch('/api/overrides').then(r => r.json()).then(data => {
        cachedOverrides = data || {};
    }).catch(() => { cachedOverrides = {}; });

    const setSmartWeights = (sector) => {
        let w = { dcf: 25, peg: 25, relative: 25, lynch: 25 }; 
        const s = sector || '';
        
        if(s.includes('Financial') || s.includes('Real Estate')) {
            w = { dcf: 0, peg: 10, relative: 60, lynch: 30 };
        } else if(s.includes('Technology') || s.includes('Communication')) {
            w = { dcf: 25, peg: 25, relative: 10, lynch: 40 };
        } else if(s.includes('Healthcare') || s.includes('Defensive') || s.includes('Utilities')) {
            w = { dcf: 50, peg: 10, relative: 20, lynch: 20 };
        } else if(s.includes('Industrials') || s.includes('Energy') || s.includes('Basic Materials') || s.includes('Cyclical')) {
            w = { dcf: 30, peg: 10, relative: 40, lynch: 20 };
        }
        
        customWeights = w;
        
        // Sync UI
        const dcfInput = document.getElementById('weight-dcf');
        if(dcfInput) dcfInput.value = w.dcf;
        const pegInput = document.getElementById('weight-peg');
        if(pegInput) pegInput.value = w.peg;
        const relInput = document.getElementById('weight-relative');
        if(relInput) relInput.value = w.relative;
        const lynInput = document.getElementById('weight-lynch');
        if(lynInput) lynInput.value = w.lynch;
        
        return w;
    };

    // Data elements
    const elements = {
        name: document.getElementById('company-name'),
        ticker: document.getElementById('company-ticker'),
        currentPrice: document.getElementById('current-price'),
        fairValue: document.getElementById('fair-value'),
        marginSafety: document.getElementById('margin-safety'),
        dcfValue: document.getElementById('dcf-value'),
        relativeValue: document.getElementById('relative-value'),
        lynchValue: document.getElementById('lynch-value'),
        pegValue: document.getElementById('peg-value')
    };

    // Safe Percentage Formatter for Tables
    const formatSafePct = (val) => {
        if (val === null || val === undefined || val === '') return 'N/A';
        return (val * 100).toFixed(2) + '%';
    };

    // INJECT CUSTOM WEIGHTS UI WITH SMART AI BTN
    const injectWeightsUI = () => {
        if(document.getElementById('weights-modal')) return;
        const modalHtml = `
            <div id="weights-modal" class="modal-overlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:9999; justify-content:center; align-items:center; backdrop-filter: blur(4px);">
                <div class="glass-card" style="width:90%; max-width:350px; padding:20px; position:relative; display:flex; flex-direction:column; gap:15px; border: 1px solid rgba(255,255,255,0.1);">
                    <h3 style="margin:0; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:10px; font-size:1.2rem; color:white;">Model Weights (%)</h3>
                    
                    <button id="smart-weights-btn" style="background: rgba(56, 189, 248, 0.1); color: #38bdf8; border: 1px solid #38bdf8; padding: 8px; border-radius: 6px; font-weight: bold; cursor: pointer; transition: 0.2s;">🪄 Auto-Set by Sector</button>
                    
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                        <label style="font-weight:600; color:var(--text-main);">DCF Model</label>
                        <input type="number" id="weight-dcf" min="0" max="100" style="width:70px; padding:6px; text-align:right; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.2); color:white; border-radius:4px; outline:none;">
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <label style="font-weight:600; color:var(--text-main);">Relative Valuation</label>
                        <input type="number" id="weight-relative" min="0" max="100" style="width:70px; padding:6px; text-align:right; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.2); color:white; border-radius:4px; outline:none;">
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <label style="font-weight:600; color:var(--text-main);">Forward Multiple</label>
                        <input type="number" id="weight-lynch" min="0" max="100" style="width:70px; padding:6px; text-align:right; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.2); color:white; border-radius:4px; outline:none;">
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <label style="font-weight:600; color:var(--text-main);">PEG Valuation</label>
                        <input type="number" id="weight-peg" min="0" max="100" style="width:70px; padding:6px; text-align:right; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.2); color:white; border-radius:4px; outline:none;">
                    </div>
                    
                    <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:15px;">
                        <button id="close-weights-btn" style="padding:8px 16px; border-radius:6px; background:transparent; border:1px solid rgba(255,255,255,0.2); color:white; cursor:pointer;">Cancel</button>
                        <button id="save-weights-btn" style="padding:8px 16px; border-radius:6px; background:var(--accent); color:#000; border:none; font-weight:bold; cursor:pointer;">Apply Weights</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        const fvContainer = elements.fairValue.closest('.glass-card') || elements.fairValue.parentElement;
        if(fvContainer) {
            fvContainer.style.position = 'relative';
            const btnHtml = `<button id="open-weights-btn" title="Adjust Valuation Weights" style="position:absolute; top:15px; right:15px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:4px; font-size:1.1rem; padding:4px 8px; cursor:pointer; transition:0.2s;">⚖️</button>`;
            fvContainer.insertAdjacentHTML('beforeend', btnHtml);
        }

        document.getElementById('open-weights-btn').addEventListener('click', () => {
            document.getElementById('weight-dcf').value = customWeights.dcf;
            document.getElementById('weight-peg').value = customWeights.peg;
            document.getElementById('weight-relative').value = customWeights.relative;
            document.getElementById('weight-lynch').value = customWeights.lynch;
            document.getElementById('weights-modal').style.display = 'flex';
        });

        document.getElementById('close-weights-btn').addEventListener('click', () => {
            document.getElementById('weights-modal').style.display = 'none';
        });
        
        document.getElementById('smart-weights-btn').addEventListener('click', () => {
            if(!globalData || !globalData.company_profile) return;
            setSmartWeights(globalData.company_profile.sector);
            if(typeof window.triggerRecalculate === 'function') {
                window.triggerRecalculate();
            }
        });

        document.getElementById('save-weights-btn').addEventListener('click', () => {
            customWeights.dcf = parseFloat(document.getElementById('weight-dcf').value) || 0;
            customWeights.peg = parseFloat(document.getElementById('weight-peg').value) || 0;
            customWeights.relative = parseFloat(document.getElementById('weight-relative').value) || 0;
            customWeights.lynch = parseFloat(document.getElementById('weight-lynch').value) || 0;
            
            localStorage.setItem('fairValueWeights', JSON.stringify(customWeights));
            document.getElementById('weights-modal').style.display = 'none';
            
            if(typeof window.triggerRecalculate === 'function') {
                window.triggerRecalculate();
            }
        });
    };
    injectWeightsUI();
    
    // INJECT COMPARISON UI
    const injectComparisonUI = () => {
        if(document.getElementById('comparison-modal')) return;
        const modalHtml = `
            <div id="comparison-modal" class="modal-overlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:9999; justify-content:center; align-items:center; backdrop-filter: blur(8px);">
                <div class="glass-card" style="width:95%; max-width:900px; padding:25px; position:relative; display:flex; flex-direction:column; gap:20px; border: 1px solid rgba(255,255,255,0.1); overflow-x: auto; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:15px;">
                        <h3 style="margin:0; font-size:1.4rem; color:white; display:flex; align-items:center; gap:10px;">
                            <span style="font-size:1.5rem;">📊</span> Side-by-Side Comparison
                        </h3>
                        <span id="close-comparison-btn" style="cursor:pointer; font-size:2rem; color:var(--text-muted); line-height:1;">&times;</span>
                    </div>
                    <div id="comparison-table-container" style="overflow-x: auto; border-radius: 12px; background: rgba(0,0,0,0.2);"></div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        document.getElementById('close-comparison-btn').onclick = () => {
            document.getElementById('comparison-modal').style.display = 'none';
            document.body.style.overflow = '';
        };
    };
    injectComparisonUI();

    const formatBigNumber = (num, pfx = '') => {
        if (num == null || isNaN(num)) return 'N/A';
        const absNum = Math.abs(num);
        if (absNum >= 1e12) return pfx + (num / 1e12).toFixed(2) + 'T';
        if (absNum >= 1e9) return pfx + (num / 1e9).toFixed(2) + 'B';
        if (absNum >= 1e6) return pfx + (num / 1e6).toFixed(2) + 'M';
        return pfx + num.toLocaleString();
    };

    const renderComparisonModal = (prof) => {
        const container = document.getElementById('comparison-table-container');
        const mainComp = {
            ticker: prof.ticker || currentTicker,
            name: prof.name || 'Current',
            market_cap: prof.market_cap,
            pe_ratio: prof.trailing_pe,
            eps: prof.trailing_eps,
            margin: prof.operating_margin
        };
        
        const competitors = prof.competitor_metrics || [];
        const all = [mainComp, ...competitors];
        
        const fmtPE = (v) => v != null ? v.toFixed(2) + 'x' : 'N/A';
        const fmtEPS = (v) => v != null ? '$' + v.toFixed(2) : 'N/A';
        const fmtMargin = (v) => v != null ? (v * 100).toFixed(2) + '%' : 'N/A';

        let html = `<table style="width:100%; border-collapse:collapse; margin-top:10px; min-width: 600px;">
            <thead style="border-bottom: 2px solid rgba(255,255,255,0.1);">
                <tr>
                    <th style="padding:12px; text-align:left; color:var(--text-muted); font-size:0.85rem;">METRIC</th>
                    ${all.map((c, i) => `<th style="padding:12px; text-align:right; color:${i === 0 ? 'var(--accent)' : 'white'};">${c.ticker}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding:12px; color:var(--text-muted);">Market Cap</td>
                    ${all.map(c => `<td style="padding:12px; text-align:right; font-weight:bold;">${formatBigNumber(c.market_cap || c.marketCap, '$')}</td>`).join('')}
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding:12px; color:var(--text-muted);">P/E (Trailing)</td>
                    ${all.map(c => `<td style="padding:12px; text-align:right; font-weight:bold;">${fmtPE(c.pe_ratio || c.pe_ratio)}</td>`).join('')}
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding:12px; color:var(--text-muted);">EPS (Trailing)</td>
                    ${all.map(c => `<td style="padding:12px; text-align:right; font-weight:bold;">${fmtEPS(c.eps || c.trailing_eps)}</td>`).join('')}
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding:12px; color:var(--text-muted);">Operating Margin</td>
                    ${all.map(c => `<td style="padding:12px; text-align:right; font-weight:bold;">${fmtMargin(c.margin || c.margin)}</td>`).join('')}
                </tr>
            </tbody>
        </table>`;
        
        container.innerHTML = html;
        document.getElementById('comparison-modal').style.display = 'flex';
        document.body.style.overflow = 'hidden';
    };

    const analyzeTicker = async (queryParam) => {
        const query = (queryParam && typeof queryParam === 'string') ? queryParam : tickerInput.value.trim();
        if (!query) return;

        // Fetch fresh overrides from server (ensures real-time cross-device sync)
        fetch('/api/overrides')
            .then(r => r.json())
            .then(data => { cachedOverrides = data || {}; })
            .catch(() => {});

        ['fcf-source', 'lynch-eps-source', 'peg-eps-source'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = 'analyst';
        });
        const lynchMult = document.getElementById('lynch-multiple');
        if (lynchMult) lynchMult.value = 'PE 20';

        ['dcf-custom-inputs', 'lynch-custom-multiple-inputs', 'lynch-custom-inputs', 'peg-custom-inputs', 'dcf-custom-input-group', 'lynch-custom-input-group', 'peg-custom-input-group', 'dcf-buyback-custom-inputs'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });

        ['dcf-custom-growth', 'dcf-custom-wacc', 'dcf-custom-perp', 'lynch-custom-mult', 'lynch-custom-growth', 'peg-custom-growth', 'dcf-custom-buyback'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });

        const selectorDefaults = {
            'fcf-source': 'analyst',
            'dcf-buyback-source': 'none',
            'relative-variant': 'peers',
            'lynch-multiple': 'PE 20',
            'lynch-eps-source': 'analyst',
            'peg-eps-source': 'analyst'
        };
        Object.entries(selectorDefaults).forEach(([id, val]) => {
            const el = document.getElementById(id);
            if (el) el.value = val;
        });

        autocompleteList.style.display = 'none';
        watchlistView.style.display = 'none';
        dashboard.style.display = 'none';
        loadingState.style.display = 'flex';

        try {
            const response = await fetch(`/api/valuation/${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();
            displayData(data);

        } catch (error) {
            console.error('Error fetching valuation:', error);
            alert('Error: ' + error.message + '\nStack: ' + error.stack);
            loadingState.style.display = 'none';
        }
    };

    const formatCurrency = (val) => val != null ? `$${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'N/A';
    const formatPercent = (val) => val != null ? `${val.toFixed(2)}%` : '0%';

    const displayData = (data) => {
        globalData = data; 
        currentFormulaData = data.formula_data;
        currentTicker = data.ticker;

        // Auto-Set Weights by Sector by Default
        if (data.company_profile && data.company_profile.sector && typeof setSmartWeights === 'function') {
            setSmartWeights(data.company_profile.sector);
        }

        elements.name.textContent = data.name;
        elements.ticker.textContent = data.ticker;
        elements.currentPrice.textContent = formatCurrency(data.current_price);

        // RED FLAGS BANNER INJECTION
        const profileHeader = document.querySelector('.profile-header') || elements.currentPrice.parentElement;
        if (profileHeader) {
            let rfBanner = document.getElementById('red-flags-banner');
            if (data.red_flags && data.red_flags.length > 0) {
                if (!rfBanner) {
                    rfBanner = document.createElement('div');
                    rfBanner.id = 'red-flags-banner';
                    rfBanner.style.cssText = 'background: rgba(239, 68, 68, 0.1); border: 1px solid var(--danger); padding: 12px; border-radius: 8px; margin-bottom: 15px; width: 100%;';
                    profileHeader.insertAdjacentElement('afterend', rfBanner);
                }
                rfBanner.innerHTML = data.red_flags.map(f => `<div style="color: var(--danger); font-weight: bold; font-size: 0.9em; margin-bottom: 4px;">${f}</div>`).join('');
                rfBanner.style.display = 'block';
            } else if (rfBanner) {
                rfBanner.style.display = 'none';
            }
        }

        // SYNC WATCHLIST
        if (watchlist.includes(data.ticker)) {
            if (!cachedWatchlistData) cachedWatchlistData = [];
            let idx = cachedWatchlistData.findIndex(d => d.ticker === data.ticker);
            if (idx !== -1) {
                cachedWatchlistData[idx] = { ...data };
            } else {
                cachedWatchlistData.push({ ...data });
            }
        }

        // DESCRIPTION CARD INJECTION
        const fvContainer = elements.fairValue.closest('.glass-card');
        if (fvContainer) {
            let descCard = document.getElementById('company-desc-card');
            if (!descCard) {
                fvContainer.insertAdjacentHTML('afterend', '<div id="company-desc-card" class="glass-card" style="margin-top: 15px; padding: 20px;"><h3 style="font-size: 0.9rem; color: var(--text-muted); margin-top: 0; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px;">Company Overview</h3><div id="company-desc-text" style="font-size: 0.95rem; line-height: 1.6; color: white; max-height: 180px; overflow-y: auto; text-align: justify; padding-right: 8px;"></div></div>');
                descCard = document.getElementById('company-desc-card');
            }
            document.getElementById('company-desc-text').textContent = data.company_profile.business_summary || 'Description not available.';
        }

        updateWatchlistButtonState();

        const setValuationStatus = (value, price, statusElemId, valueElemId) => {
            const statusElem = document.getElementById(statusElemId);
            const valueElem = document.getElementById(valueElemId);

            if (value == null || price == null) {
                if (statusElem) {
                    statusElem.textContent = "N/A";
                    statusElem.style.color = "var(--text-muted)";
                }
                if (valueElem) valueElem.textContent = "N/A";
                return;
            }

            if (!valueElem || !statusElem) return;

            valueElem.textContent = formatCurrency(value);

            const diffPct = (value - price) / price;
            if (diffPct >= 0.05) {
                statusElem.textContent = "Undervalued";
                statusElem.style.color = "var(--accent)";
            } else if (diffPct <= -0.05) {
                statusElem.textContent = "Overvalued";
                statusElem.style.color = "var(--danger)";
            } else {
                statusElem.textContent = "Fair Valued";
                statusElem.style.color = "#fbbf24";
            }
        };
        
        const dcfCardMosRow = document.getElementById('dcf-card-mos-row');
        const dcfCardPrice = document.getElementById('dcf-card-price');
        const dcfCardMos = document.getElementById('dcf-card-mos');
        if (dcfCardMosRow && data.formula_data && data.formula_data.dcf) {
            const dcf = data.formula_data.dcf;
            dcfCardMosRow.style.display = 'flex';
            dcfCardPrice.textContent = `Price: ${formatCurrency(dcf.current_price)}`;
            if (dcf.margin_of_safety != null) {
                const mos = dcf.margin_of_safety;
                dcfCardMos.textContent = `MOS: ${formatPercent(mos)}`;
                dcfCardMos.style.color = mos > 0 ? 'var(--accent)' : 'var(--danger)';
            } else {
                dcfCardMos.textContent = 'MOS: N/A';
                dcfCardMos.style.color = 'var(--text-muted)';
            }
        } else if (dcfCardMosRow) {
            dcfCardMosRow.style.display = 'none';
        }

        const updateScoreUI = (scoreVal, circleId, fillId) => {
            const circle = document.getElementById(circleId);
            const fill = document.getElementById(fillId);
            if (!circle || !fill) return;

            circle.className = 'score-circle';
            fill.className = 'score-bar-fill';
            circle.style.color = '';
            fill.style.backgroundColor = '';
            fill.style.width = '0%';

            if (scoreVal === "N/A" || scoreVal == null) {
                circle.textContent = "N/A";
                circle.style.color = "var(--text-muted)";
                fill.style.backgroundColor = "var(--text-muted)";
                return;
            }

            circle.textContent = scoreVal;
            setTimeout(() => {
                fill.style.width = `${scoreVal}%`;
            }, 50);

            if (scoreVal >= 76) {
                circle.classList.add('score-green');
                fill.classList.add('bg-score-green');
            } else if (scoreVal >= 41) {
                circle.classList.add('score-yellow');
                fill.classList.add('bg-score-yellow');
            } else {
                circle.classList.add('score-red');
                fill.classList.add('bg-score-red');
            }
        };

        currentHealthBreakdown = data.health_breakdown;
        currentBuyBreakdown = data.buy_breakdown;

        updateScoreUI(data.health_score, 'health-score-circle', 'health-score-fill');
        updateScoreUI(data.buy_score, 'buy-score-circle', 'buy-score-fill');

        // Bind click handlers on score rows (must be done here, after data is loaded)
        const healthRow = document.getElementById('health-score-row') || document.getElementById('health-score-circle')?.closest('.score-row');
        console.log('[Score Handlers] healthRow:', healthRow, 'breakdown:', currentHealthBreakdown?.length);
        if (healthRow) {
            healthRow.style.cursor = 'pointer';
            healthRow.onclick = function() {
                console.log('[Score Click] Health clicked!');
                renderScoreBreakdown('Company Health Breakdown', data.health_score, currentHealthBreakdown);
            };
        }
        const buyRow = document.getElementById('buy-score-row') || document.getElementById('buy-score-circle')?.closest('.score-row');
        console.log('[Score Handlers] buyRow:', buyRow, 'breakdown:', currentBuyBreakdown?.length);
        if (buyRow) {
            buyRow.style.cursor = 'pointer';
            buyRow.onclick = function() {
                console.log('[Score Click] Buy clicked!');
                renderScoreBreakdown('Good to Buy Score Breakdown', data.buy_score, currentBuyBreakdown);
            };
        }

        // UPDATED: Sync both MOS and PEG to the Score Breakdown dynamically
        const updateInsightsAndScores = (newMos, newPeg) => {
            if (!currentBuyBreakdown) return;

            // Update Margin of Safety
            let mosItem = currentBuyBreakdown.find(i => i.name.includes("Margin of Safety"));
            if (mosItem) {
                let pts = 0;
                let mos_str = "N/A";
                if (newMos != null) {
                    mos_str = `${newMos.toFixed(1)}%`;
                    if (newMos > 30.0) pts = 30;
                    else if (newMos >= 15.0) pts = 20;
                    else if (newMos >= 0.0) pts = 10;
                }

                if (typeof data.buy_score === 'number') {
                    data.buy_score = data.buy_score - mosItem.points + pts;
                }

                mosItem.points = pts;
                mosItem.value = mos_str;
            }

            // Update Custom PEG
            let pegItem = currentBuyBreakdown.find(i => i.name.includes("PEG Ratio"));
            if (pegItem && newPeg != null) {
                let pts = 0;
                let peg_str = `${newPeg.toFixed(2)}x`;
                
                let max_p = pegItem.max_points || 20; 
                if (newPeg <= 1.0 && newPeg > 0) pts = max_p;
                else if (newPeg <= 1.5 && newPeg > 0) pts = Math.floor(max_p / 2);
                
                if (typeof data.buy_score === 'number') {
                    data.buy_score = data.buy_score - pegItem.points + pts;
                }
                
                pegItem.points = pts;
                pegItem.value = peg_str;
            }

            if (typeof data.buy_score === 'number') {
                updateScoreUI(data.buy_score, 'buy-score-circle', 'buy-score-fill');
            }

            const allMetrics = [...(currentHealthBreakdown || []), ...(currentBuyBreakdown || [])];
            const strengths = allMetrics.filter(m => m.points === m.max_points && m.max_points > 0);
            strengths.sort((a, b) => b.max_points - a.max_points);
            const topStrengths = strengths.slice(0, 3);

            const risks = allMetrics.filter(m => m.points === 0 || (m.max_points > 0 && m.points <= (m.max_points / 3)));
            risks.sort((a, b) => (a.points / a.max_points) - (b.points / b.max_points));
            const topRisks = risks.slice(0, 3);

            const strengthsList = document.getElementById('top-strengths-list');
            if (strengthsList) {
                strengthsList.innerHTML = '';
                if (topStrengths.length > 0) {
                    topStrengths.forEach(s => {
                        const li = document.createElement('li');
                        li.innerHTML = `<strong>${s.name.split(' (')[0]}:</strong> ${s.value}`;
                        strengthsList.appendChild(li);
                    });
                } else {
                    strengthsList.innerHTML = '<li>No major strengths detected.</li>';
                }
            }

            const risksList = document.getElementById('risk-factors-list');
            if (risksList) {
                risksList.innerHTML = '';
                if (topRisks.length > 0) {
                    topRisks.forEach(r => {
                        const li = document.createElement('li');
                        li.innerHTML = `<strong>${r.name.split(' (')[0]}:</strong> ${r.value}`;
                        risksList.appendChild(li);
                    });
                } else {
                    risksList.innerHTML = '<li>No critical risks detected.</li>';
                }
            }
        };

        const calcLocalDcf = (fcf, growth, wacc, perp, shares, cash, debt, buybackRate = 0, years = 5) => {
            if (!fcf || !shares || shares <= 0) return null;
            let pv = 0;
            let f = fcf;
            for (let i = 1; i <= years; i++) {
                f *= (1 + growth);
                pv += f / Math.pow(1 + wacc, i);
            }
            const tv = (f * (1 + perp)) / (wacc - perp);
            const pvTv = tv / Math.pow(1 + wacc, years);
            const ev = pv + pvTv;
            const eqVal = ev + (cash || 0) - (debt || 0);
            if (eqVal <= 0) return null;
            const effectiveShares = shares * Math.pow(1 - (buybackRate || 0), years);
            return eqVal / (effectiveShares > 0 ? effectiveShares : shares);
        };

        const updateFairValue = () => {
            if (!currentFormulaData) return;
            const prof = data.company_profile;

            let dcfVal = null;
            if (currentFormulaData.dcf) {
                const fcfSourceEl = document.getElementById('fcf-source');
                const fcfSource = fcfSourceEl ? fcfSourceEl.value : 'analyst';
                const yearsSourceEl = document.getElementById('dcf-years-source');
                const yearsVal = yearsSourceEl ? yearsSourceEl.value : '5yr';
                const years = yearsVal === '10yr' ? 10 : 5;
                const dcfData = currentFormulaData.dcf[yearsVal] || currentFormulaData.dcf["5yr"];
                
                const dcfInputs = document.getElementById('dcf-custom-inputs');
                if (dcfInputs) dcfInputs.style.display = fcfSource === 'custom' ? 'flex' : 'none';

                const buybackEl = document.getElementById('dcf-buyback-source');
                const buybackSrc = buybackEl ? buybackEl.value : 'none';
                const buybackCustomInputs = document.getElementById('dcf-buyback-custom-inputs');
                if (buybackCustomInputs) buybackCustomInputs.style.display = buybackSrc === 'custom' ? 'flex' : 'none';

                let buybackRate = 0;
                if (buybackSrc === 'historical') {
                    buybackRate = currentFormulaData.dcf.historic_buyback_rate || 0;
                } else if (buybackSrc === 'custom') {
                    buybackRate = parseFloat(document.getElementById('dcf-custom-buyback').value) / 100 || 0;
                }

                const baseFcf = currentFormulaData.dcf.fcf;
                const shares = prof.shares_outstanding;

                if (fcfSource === 'analyst') {
                    const waccInput = document.getElementById('dcf-custom-wacc');
                    const backendWacc = currentFormulaData.dcf.discount_rate;
                    if (waccInput && !waccInput.value && backendWacc) {
                         waccInput.value = (backendWacc * 100).toFixed(2);
                    }
                    
                    if (buybackRate === 0 && (!waccInput || !waccInput.value || parseFloat(waccInput.value)/100 === backendWacc)) {
                        dcfVal = dcfData ? dcfData.intrinsic_value : currentFormulaData.dcf.intrinsic_value;
                    } else {
                        const g = currentFormulaData.dcf.eps_growth_estimated || 0.10;
                        const w = waccInput && waccInput.value ? parseFloat(waccInput.value)/100 : (currentFormulaData.dcf.discount_rate || 0.09);
                        const p = currentFormulaData.dcf.perpetual_growth || 0.02;
                        dcfVal = calcLocalDcf(baseFcf, g, w, p, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years);
                    }
                } else if (fcfSource === 'historical') {
                    const hg = prof.historic_fcf_growth != null ? prof.historic_fcf_growth : 0.05;
                    dcfVal = calcLocalDcf(baseFcf, hg, 0.09, 0.02, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years);
                } else if (fcfSource === 'custom') {
                    const g = parseFloat(document.getElementById('dcf-custom-growth').value) / 100 || 0.15;
                    const w = parseFloat(document.getElementById('dcf-custom-wacc').value) / 100 || 0.09;
                    const p = parseFloat(document.getElementById('dcf-custom-perp').value) / 100 || 0.025;
                    dcfVal = calcLocalDcf(baseFcf, g, w, p, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years);
                }
            }
            setValuationStatus(dcfVal, data.current_price, 'dcf-status', 'dcf-value');

            let pegVal = null;
            let pegMos = null;
            let usedGrowth = 0;
            let currentPegToDisplay = null;

            if (currentFormulaData.peg) {
                const pegSrcEl = document.getElementById('peg-eps-source');
                const pegSrc = pegSrcEl ? pegSrcEl.value : 'analyst';
                const pegInputs = document.getElementById('peg-custom-inputs');
                if (pegInputs) pegInputs.style.display = pegSrc === 'custom' ? 'flex' : 'none';

                usedGrowth = currentFormulaData.peg.eps_growth_estimated || 0;
                if (pegSrc === 'custom') {
                    usedGrowth = (parseFloat(document.getElementById('peg-custom-growth').value) || 20) / 100;
                }

                const currentPe = currentFormulaData.peg.current_pe || (parseFloat(data.company_profile.trailing_pe) || 0);
                const industryPeg = currentFormulaData.peg.industry_peg;

                if (usedGrowth > 0 && currentPe > 0 && industryPeg != null && industryPeg > 0) {
                    currentPegToDisplay = currentPe / (usedGrowth * 100);
                    pegVal = data.current_price * (industryPeg / currentPegToDisplay);
                    pegMos = ((pegVal - data.current_price) / pegVal) * 100;
                } else if (pegSrc === 'analyst') {
                    pegVal = currentFormulaData.peg.fair_value;
                    pegMos = currentFormulaData.peg.margin_of_safety;
                    currentPegToDisplay = currentFormulaData.peg.current_peg;
                }
            }
            
            const pegValueElem = document.getElementById('peg-value');
            if (pegValueElem) {
                pegValueElem.textContent = pegVal != null ? formatCurrency(pegVal) : 'N/A';
                pegValueElem.style.color = pegVal != null ? 'var(--accent)' : 'var(--text-muted)';
            }
            
            const pegStatusElem = document.getElementById('peg-status');
            const pegCompareElem = document.getElementById('peg-compare');
            
            if (pegStatusElem && pegCompareElem) {
                const industryPeg = currentFormulaData.peg ? currentFormulaData.peg.industry_peg : null;

                if (pegVal != null && industryPeg != null && currentPegToDisplay != null) {
                    const sectorPegDisplay = industryPeg.toFixed(2);
                    pegCompareElem.textContent = `PEG = ${currentPegToDisplay.toFixed(2)} vs PEG Sector = ${sectorPegDisplay}`;
                    
                    if (pegMos != null) {
                        const mosText = `${pegMos > 0 ? '+' : ''}${pegMos.toFixed(2)}% Margin of Safety`;
                        pegCompareElem.innerHTML += `<br><span style="color: ${pegMos > 0 ? 'var(--accent)' : 'var(--danger)'}; font-weight: 600;">${mosText}</span>`;
                    }

                    if (data.current_price < pegVal) {
                        pegStatusElem.textContent = `Undervalued`;
                        pegStatusElem.style.color = 'var(--accent)';
                    } else {
                        pegStatusElem.textContent = `Overvalued`;
                        pegStatusElem.style.color = 'var(--danger)';
                    }
                } else {
                    pegStatusElem.textContent = "N/A";
                    pegStatusElem.style.color = "var(--text-muted)";
                    pegCompareElem.textContent = industryPeg == null ? "Sector data unavailable" : "PEG calculation data missing";
                }
            }

            let lynchVal = null;
            if (currentFormulaData.peter_lynch) {
                const pl = currentFormulaData.peter_lynch;
                const epsSourceEl = document.getElementById('lynch-eps-source');
                const epsSource = epsSourceEl ? epsSourceEl.value : 'analyst';
                const lynchInputs = document.getElementById('lynch-custom-inputs');
                if (lynchInputs) lynchInputs.style.display = epsSource === 'custom' ? 'flex' : 'none';

                let usedGrowth = pl.eps_growth_estimated || 0.05;
                let targetEps = (pl.trailing_eps || 0) * Math.pow(1 + usedGrowth, 3);

                if (epsSource === 'historical') {
                    usedGrowth = prof.historic_eps_growth != null ? prof.historic_eps_growth : 0.05;
                    targetEps = (pl.trailing_eps || 0) * Math.pow(1 + usedGrowth, 3);
                } else if (epsSource === 'custom') {
                    usedGrowth = parseFloat(document.getElementById('lynch-custom-growth').value) / 100 || 0.20;
                    targetEps = (pl.trailing_eps || 0) * Math.pow(1 + usedGrowth, 3);
                }

                const multEl = document.getElementById('lynch-multiple');
                const multVal = multEl ? multEl.value : 'PE 20';
                const multCustomInputs = document.getElementById('lynch-custom-multiple-inputs');
                if (multCustomInputs) multCustomInputs.style.display = multVal === 'custom' ? 'flex' : 'none';

                let selectedMult = 20; 
                if (multVal === 'PE 15') selectedMult = 15;
                if (multVal === 'PE 20') selectedMult = 20;
                if (multVal === 'PE 25') selectedMult = 25;
                if (multVal === 'historic') selectedMult = pl.historic_pe || 20;
                if (multVal === 'custom') {
                    selectedMult = parseFloat(document.getElementById('lynch-custom-mult').value) || 18;
                }

                if (targetEps != null && targetEps > 0) {
                    lynchVal = targetEps * selectedMult;
                }
                
                // Keep the global data updated with what we are currently viewing
                // so Watchlist extraction pulls the currently viewed value instead of default
                if(lynchVal != null) {
                    currentFormulaData.peter_lynch.fair_value_pe_20 = lynchVal; 
                }
            }

            setValuationStatus(lynchVal, data.current_price, 'lynch-status', 'lynch-fair-value');

            let relVal = null;
            const rel = currentFormulaData.relative;
            if (rel) {
                const fvMedian = (rel.median_peer_pe != null && rel.company_eps != null) ? rel.median_peer_pe * rel.company_eps : null;
                const fvMean = (rel.mean_peer_pe != null && rel.company_eps != null) ? rel.mean_peer_pe * rel.company_eps : null;
                const fvSP500 = (rel.market_pe_trailing != null && rel.company_eps != null) ? rel.market_pe_trailing * rel.company_eps : null;

                const variantEl = document.getElementById('relative-variant');
                const variant = variantEl ? variantEl.value : 'peers';

                if (variant === 'peers') relVal = fvMedian;
                else if (variant === 'average') relVal = fvMean;
                else if (variant === 'sp500') relVal = fvSP500;

                const mc = document.getElementById('relative-market-compare');
                if (mc) {
                    const mpe = rel.market_pe_trailing != null ? rel.market_pe_trailing.toFixed(1) + 'x' : '--';
                    const peerMedianPe = rel.median_peer_pe != null ? rel.median_peer_pe.toFixed(1) + 'x' : '--';
                    const peerMeanPe = rel.mean_peer_pe != null ? rel.mean_peer_pe.toFixed(1) + 'x' : '--';

                    if (variant === 'peers') mc.textContent = `Peer Median P/E: ${peerMedianPe}`;
                    else if (variant === 'average') mc.textContent = `Peer Mean P/E: ${peerMeanPe}`;
                    else if (variant === 'sp500') mc.textContent = `S&P 500 Trailing P/E: ${mpe}`;
                }
            }
            setValuationStatus(relVal, data.current_price, 'relative-status', 'relative-value');
            
            // --- CALCULATE FINAL FAIR VALUE ---
            const hasUserWeights = localStorage.getItem('fairValueWeights') !== null;
            const modelsToggled = !document.getElementById('toggle-peter_lynch').checked || 
                                 !document.getElementById('toggle-peg').checked || 
                                 !document.getElementById('toggle-relative').checked || 
                                 !document.getElementById('toggle-dcf').checked;

            let finalFv = data.fair_value;
            let finalMos = data.margin_of_safety;

            if (hasUserWeights || modelsToggled) {
                let totalWeight = 0;
                let weightedSum = 0;

                const addVal = (val, isChecked, weightKey) => {
                    if (val != null && val > 0 && isChecked) {
                        const w = customWeights[weightKey] || 0;
                        totalWeight += w;
                        weightedSum += (val * w);
                    }
                };

                addVal(lynchVal, document.getElementById('toggle-peter_lynch').checked, 'lynch');
                addVal(pegVal, document.getElementById('toggle-peg').checked, 'peg');
                addVal(relVal, document.getElementById('toggle-relative').checked, 'relative');
                addVal(dcfVal, document.getElementById('toggle-dcf').checked, 'dcf');

                if (totalWeight > 0) {
                    finalFv = weightedSum / totalWeight;
                    finalMos = ((finalFv - data.current_price) / finalFv) * 100;
                }
            }

            if (finalFv != null) {
                elements.fairValue.textContent = formatCurrency(finalFv);
                elements.marginSafety.textContent = `${formatPercent(finalMos)} Margin of Safety`;
                elements.marginSafety.style.color = finalMos > 0 ? 'var(--accent)' : 'var(--danger)';
                if (finalMos > 0) {
                    elements.marginSafety.style.background = 'rgba(16, 185, 129, 0.2)';
                } else {
                    elements.marginSafety.style.background = 'rgba(239, 68, 68, 0.2)';
                }
                updateInsightsAndScores(finalMos, currentPegToDisplay);
            } else {
                elements.fairValue.textContent = 'N/A';
                elements.marginSafety.textContent = 'Valuation not possible';
                elements.marginSafety.style.color = 'var(--text-muted)';
                elements.marginSafety.style.background = 'none';
                updateInsightsAndScores(null, currentPegToDisplay);
            }
        };

        window.triggerRecalculate = updateFairValue;

        const inputSelectors = [
            'fcf-source', 'dcf-years-source', 'dcf-custom-growth', 'dcf-custom-wacc', 'dcf-custom-perp',
            'dcf-buyback-source', 'dcf-custom-buyback', 'relative-variant',
            'lynch-multiple', 'lynch-custom-mult', 'lynch-eps-source', 'lynch-custom-growth',
            'peg-eps-source', 'peg-custom-growth'
        ];
          const updateAndSave = () => {
            updateFairValue();
            saveOverridesDebounced(currentTicker);
        };

        inputSelectors.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                if (el.tagName === 'SELECT') el.onchange = updateAndSave;
                else el.oninput = updateAndSave;
            }
        });

        // Restore overrides BEFORE first updateFairValue
        const hadOverrides = applyOverrides(currentTicker);
        updateFairValue();

        document.querySelectorAll('.valuation-toggle').forEach(toggle => {
            toggle.onchange = updateAndSave;
        });

        const pBody = document.getElementById('profile-body');
        if (pBody && data.company_profile) {
            const prof = data.company_profile;

            // UPDATED: Replaced bad *100 formatting with safe formatSafePct
            pBody.innerHTML = `
                <tr><td class="profile-label">Next Earnings</td><td class="profile-value" style="color: var(--accent); font-weight: bold;">${prof.next_earnings_date || 'N/A'}</td></tr>
                <tr><td class="profile-label">Industry</td><td class="profile-value">${prof.industry}<br><span style="font-size: 0.85em; font-weight: normal; color: var(--text-muted);">${prof.sector}</span></td></tr>
                <tr><td class="profile-label">Market Cap</td><td class="profile-value">${formatBigNumber(prof.market_cap, '$')}</td></tr>
                <tr><td class="profile-label">Operating Margin</td><td class="profile-value">${formatSafePct(prof.operating_margin)}</td></tr>
                <tr><td class="profile-label">Net Margin</td><td class="profile-value">${formatSafePct(prof.net_margin)}</td></tr>
                <tr><td class="profile-label">P/E (Trailing)</td><td class="profile-value">${prof.trailing_pe ? prof.trailing_pe.toFixed(2) + 'x' : 'N/A'}</td></tr>
                <tr><td class="profile-label">EPS (Trailing)</td><td class="profile-value">${prof.trailing_eps ? '$' + prof.trailing_eps.toFixed(2) : 'N/A'}</td></tr>
                <tr><td class="profile-label">Debt-to-Equity</td><td class="profile-value">${prof.debt_to_equity != null ? prof.debt_to_equity.toFixed(2) + 'x' : 'N/A'}</td></tr>
                <tr><td class="profile-label">Insider Ownership</td><td class="profile-value">${formatSafePct(prof.insider_ownership)}</td></tr>
                <tr><td class="profile-label">Shares Out.</td><td class="profile-value">${formatBigNumber(prof.shares_outstanding, '')}</td></tr>
                <tr><td class="profile-label">Buyback rate</td><td class="profile-value">${prof.buyback_rate != null ? (prof.buyback_rate > 0 ? '+' : '') + prof.buyback_rate.toFixed(2) + '%' : 'N/A'}</td></tr>
                <tr><td class="profile-label">Dividend Yield</td><td class="profile-value">${formatSafePct(prof.dividend_yield)}</td></tr>
                <tr><td class="profile-label">Payout Ratio</td><td class="profile-value">${prof.payout_ratio > 0.80 ? `<span style="color:var(--danger); font-weight:bold;">${formatSafePct(prof.payout_ratio)}</span>` : formatSafePct(prof.payout_ratio)}</td></tr>
                <tr><td class="profile-label">Dividend Streak</td><td class="profile-value">${prof.dividend_streak != null ? prof.dividend_streak + ' Years' : 'N/A'}</td></tr>
                <tr><td class="profile-label">5Y Div Growth (CAGR)</td><td class="profile-value">${formatSafePct(prof.dividend_cagr_5y)}</td></tr>
                <tr><td class="profile-label" style="white-space: nowrap;">Competitors ${prof.competitor_metrics && prof.competitor_metrics.length > 0 ? `<button id="compare-peers-btn" style="margin-left: 8px; background: rgba(56, 189, 248, 0.1); color: #38bdf8; border: 1px solid #38bdf8; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; cursor: pointer; transition: 0.2s; font-weight: bold;">📊 Compare Peers</button>` : ''}</td><td class="profile-value" style="word-wrap: break-word;">${prof.competitors && prof.competitors.length ? prof.competitors.join(', ') : 'None'}</td></tr>
            `;

            if(document.getElementById('compare-peers-btn')) {
                document.getElementById('compare-peers-btn').onclick = () => renderComparisonModal(prof);
            }
        }

        const trendsBody = document.getElementById('trends-body');
        if (trendsBody) {
            if (data.historical_trends && data.historical_trends.length > 0) {
                let html = '';
                data.historical_trends.forEach(row => {
                    if (row.revenue == null && row.net_margin == null && row.fcf == null) return;
                    
                    const revStr = row.revenue != null ? (row.revenue / 1e9).toFixed(2) : '-';
                    const marginStr = row.net_margin != null ? (row.net_margin * 100).toFixed(1) + '%' : '-';
                    const fcfStr = row.fcf != null ? (row.fcf / 1e9).toFixed(2) : '-';
                    html += `<tr><td>${row.year}</td><td>${revStr}</td><td>${marginStr}</td><td>${fcfStr}</td></tr>`;
                });
                trendsBody.innerHTML = html;
            } else {
                trendsBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 1rem;">No historical trends available.</td></tr>';
            }
        }

        loadingState.style.display = 'none';
        watchlistView.style.display = 'none';
        dashboard.style.display = 'block';

        renderAnalystEstimatesInline(data.ticker);
        renderHistoricalCharts(data);
    };

    let currentSort = { column: 'mos', order: 'desc' };
    let cachedWatchlistData = null;

    const saveWatchlist = () => {
        localStorage.setItem('fairValueWatchlist', JSON.stringify(watchlist));
        fetch('/api/watchlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tickers: watchlist })
        }).catch(err => console.error('Watchlist sync error:', err));
    };

    // --- Overrides Sync ---
    const overrideInputIds = [
        'fcf-source', 'dcf-years-source', 'dcf-custom-growth', 'dcf-custom-wacc', 'dcf-custom-perp',
        'dcf-buyback-source', 'dcf-custom-buyback', 'relative-variant',
        'lynch-multiple', 'lynch-custom-mult', 'lynch-eps-source', 'lynch-custom-growth',
        'peg-eps-source', 'peg-custom-growth'
    ];
    const overrideToggleIds = ['toggle-dcf', 'toggle-relative', 'toggle-peter_lynch', 'toggle-peg'];

    const collectOverrideInputs = () => {
        const inputs = {};
        overrideInputIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) inputs[id] = el.value;
        });
        return inputs;
    };

    const collectOverrideToggles = () => {
        const toggles = {};
        overrideToggleIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) toggles[id] = el.checked;
        });
        return toggles;
    };

    const saveOverridesToServer = (ticker) => {
        if (!ticker || !watchlist.includes(ticker)) return;
        // Read current FV/MOS from DOM globally
        const fvEl = document.getElementById('fair-value');
        const mosEl = document.getElementById('margin-safety');
        const fvText = fvEl ? fvEl.textContent.replace(/[^0-9.-]/g, '') : '';
        const mosText = mosEl ? mosEl.textContent : '';
        const fv = parseFloat(fvText) || null;
        const mosMatch = mosText.match(/([\-0-9.]+)%/);
        const mos = mosMatch ? parseFloat(mosMatch[1]) : null;

        const payload = {
            ticker: ticker,
            inputs: collectOverrideInputs(),
            toggles: collectOverrideToggles(),
            computed: { fair_value: fv, margin_of_safety: mos }
        };

        cachedOverrides[ticker] = payload;

        fetch('/api/overrides', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).catch(err => console.error('Override sync error:', err));
    };

    const saveOverridesDebounced = (ticker) => {
        if (overrideSaveTimer) clearTimeout(overrideSaveTimer);
        overrideSaveTimer = setTimeout(() => saveOverridesToServer(ticker), 500);
    };

    const applyOverrides = (ticker) => {
        const ov = cachedOverrides[ticker];
        if (!ov) return false;
        const inputs = ov.inputs || {};
        const toggles = ov.toggles || {};

        // Apply inputs
        Object.entries(inputs).forEach(([id, val]) => {
            const el = document.getElementById(id);
            if (el) {
                el.value = val;
                // Show/hide custom input containers based on select values
                if (id === 'fcf-source') {
                    const ci = document.getElementById('dcf-custom-inputs');
                    if (ci) ci.style.display = val === 'custom' ? 'flex' : 'none';
                }
                if (id === 'dcf-buyback-source') {
                    const ci = document.getElementById('dcf-buyback-custom-inputs');
                    if (ci) ci.style.display = val === 'custom' ? 'flex' : 'none';
                }
                if (id === 'lynch-multiple') {
                    const ci = document.getElementById('lynch-custom-multiple-inputs');
                    if (ci) ci.style.display = val === 'custom' ? 'flex' : 'none';
                }
                if (id === 'lynch-eps-source') {
                    const ci = document.getElementById('lynch-custom-inputs');
                    if (ci) ci.style.display = val === 'custom' ? 'flex' : 'none';
                }
                if (id === 'peg-eps-source') {
                    const ci = document.getElementById('peg-custom-inputs');
                    if (ci) ci.style.display = val === 'custom' ? 'flex' : 'none';
                }
            }
        });

        // Apply toggles
        Object.entries(toggles).forEach(([id, checked]) => {
            const el = document.getElementById(id);
            if (el) el.checked = checked;
        });

        return true;
    };

    const deleteOverrideFromServer = (ticker) => {
        delete cachedOverrides[ticker];
        fetch(`/api/overrides/${ticker}`, { method: 'DELETE' })
            .catch(err => console.error('Override delete error:', err));
    };

    const updateWatchlistButtonState = () => {
        if (!currentTicker) return;
        if (watchlist.includes(currentTicker)) {
            addToWatchlistBtn.classList.add('added');
            addToWatchlistBtn.innerHTML = '★';
        } else {
            addToWatchlistBtn.classList.remove('added');
            addToWatchlistBtn.innerHTML = '☆';
        }
    };

    const toggleWatchlist = () => {
        if (!currentTicker) return;
        if (watchlist.includes(currentTicker)) {
            watchlist = watchlist.filter(t => t !== currentTicker);
            deleteOverrideFromServer(currentTicker);
        } else {
            watchlist.push(currentTicker);
            saveOverridesToServer(currentTicker);
        }
        saveWatchlist();
        updateWatchlistButtonState();
    };

    let dragSrcIndex = null;
    let manualOrder = false;

    // ── Historical Charts (Chart.js) ──────────────────────────────────

    const renderHistoricalCharts = (data) => {
        const container = document.getElementById('historical-charts-container');
        if (!container) return;

        const hd = data.historical_data;
        if (!hd || !hd.years || hd.years.length === 0) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';

        const labels = hd.years;
        const estIndex = labels.findIndex(l => String(l).includes('Est'));

        // Helper: build background colors (solid for actual, translucent for estimates)
        const bgColors = (baseColor, alphaActual, alphaEst) =>
            labels.map((_, i) => i >= estIndex && estIndex !== -1
                ? baseColor.replace('1)', `${alphaEst})`)
                : baseColor.replace('1)', `${alphaActual})`));

        const borderDash = labels.map((_, i) => i >= estIndex && estIndex !== -1 ? [6, 4] : []);

        // ── Chart 1: Revenue & FCF (Bar chart, millions) ──
        const ctxRevFcf = document.getElementById('chart-rev-fcf');
        if (ctxRevFcf) {
            if (chartRevFcf) chartRevFcf.destroy();
            chartRevFcf = new Chart(ctxRevFcf, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'Revenue ($M)',
                            data: hd.revenue.map(v => v ? +(v / 1e6).toFixed(1) : 0),
                            backgroundColor: bgColors('rgba(56, 189, 248, 1)', 0.7, 0.3),
                            borderColor: 'rgba(56, 189, 248, 1)',
                            borderWidth: 1,
                            borderRadius: 4,
                            order: 2
                        },
                        {
                            label: 'FCF ($M)',
                            data: hd.fcf.map(v => v ? +(v / 1e6).toFixed(1) : 0),
                            backgroundColor: bgColors('rgba(16, 185, 129, 1)', 0.7, 0.3),
                            borderColor: 'rgba(16, 185, 129, 1)',
                            borderWidth: 1,
                            borderRadius: 4,
                            order: 2
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#94a3b8', font: { size: 11 } } },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.1)' } },
                        y: { ticks: { color: '#94a3b8', callback: v => '$' + v.toLocaleString() + 'M' }, grid: { color: 'rgba(148,163,184,0.1)' } }
                    }
                }
            });
        }

        // ── Chart 2: EPS & Shares Outstanding (Dual Axis) ──
        const ctxEps = document.getElementById('chart-eps-shares');
        if (ctxEps) {
            if (chartEpsShares) chartEpsShares.destroy();

            const epsData = hd.eps || [];
            const sharesData = (hd.shares || []).map(v => v ? +(v / 1e6).toFixed(1) : 0);

            chartEpsShares = new Chart(ctxEps, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'EPS ($)',
                            data: epsData.map(v => v ? +v.toFixed(2) : 0),
                            backgroundColor: bgColors('rgba(168, 85, 247, 1)', 0.7, 0.3),
                            borderColor: 'rgba(168, 85, 247, 1)',
                            borderWidth: 1,
                            borderRadius: 4,
                            yAxisID: 'y',
                            order: 2
                        },
                        {
                            label: 'Shares (M)',
                            data: sharesData,
                            type: 'line',
                            borderColor: 'rgba(251, 191, 36, 0.8)',
                            backgroundColor: 'rgba(251, 191, 36, 0.1)',
                            pointBackgroundColor: 'rgba(251, 191, 36, 1)',
                            pointRadius: 4,
                            borderWidth: 2,
                            fill: true,
                            tension: 0.3,
                            yAxisID: 'y1',
                            order: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#94a3b8', font: { size: 11 } } },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.1)' } },
                        y:  { position: 'left',  ticks: { color: '#a855f7', callback: v => '$' + v }, grid: { color: 'rgba(148,163,184,0.1)' }, title: { display: true, text: 'EPS ($)', color: '#a855f7' } },
                        y1: { position: 'right', ticks: { color: '#fbbf24', callback: v => v + 'M' }, grid: { drawOnChartArea: false }, title: { display: true, text: 'Shares (M)', color: '#fbbf24' } }
                    }
                }
            });
        }
    };

    const analystCard = document.getElementById('analyst-estimates-card');

    const renderAnalystEstimatesInline = async (ticker) => {
        if (!ticker || !analystCard) return;
        analystCard.style.display = 'block';
        document.getElementById('pt-avg').textContent = '...';
        document.getElementById('rec-status').textContent = '...';
        document.querySelector('#eps-est-table tbody').innerHTML = '';
        document.querySelector('#rev-est-table tbody').innerHTML = '';

        try {
            const res = await fetch(`/api/analyst/${ticker}`);
            if (!res.ok) throw new Error('API Error');
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            const pt = data.price_target || {};
            document.getElementById('pt-avg').textContent = pt.avg ? `$${pt.avg.toFixed(2)}` : '--';
            document.getElementById('pt-upside').textContent = pt.upside_pct ? `${pt.upside_pct > 0 ? '+' : ''}${pt.upside_pct.toFixed(1)}%` : '--';
            document.getElementById('pt-upside').style.color = (pt.upside_pct > 0) ? 'var(--accent)' : (pt.upside_pct < 0 ? 'var(--danger)' : 'var(--text-muted)');
            document.getElementById('pt-low').textContent = pt.low ? `$${pt.low.toFixed(2)}` : '--';
            document.getElementById('pt-high').textContent = pt.high ? `$${pt.high.toFixed(2)}` : '--';

            const rec = data.recommendation || {};
            const statusElem = document.getElementById('rec-status');
            const counts = rec.counts || {};
            const maxVal = Math.max(...Object.values(counts), 1);
            const barsContainer = document.getElementById('rec-bars');
            barsContainer.innerHTML = '';

            const labels = { strongBuy: 'S. Buy', buy: 'Buy', hold: 'Hold', sell: 'Sell', strongSell: 'S. Sell' };
            const fullLabels = { strongBuy: 'STRONG BUY', buy: 'BUY', hold: 'HOLD', sell: 'SELL', strongSell: 'STRONG SELL' };
            
            let topCategory = 'N/A';
            let topCount = -1;

            let barsHtml = '';
            ['strongBuy', 'buy', 'hold', 'sell', 'strongSell'].forEach(k => {
                const count = counts[k] || 0;
                if (count > topCount) {
                    topCount = count;
                    topCategory = fullLabels[k];
                }
                const pct = (count / maxVal) * 100;
                barsHtml += `
                    <div class="rec-bar-row">
                        <span class="rec-bar-label">${labels[k]}</span>
                        <div class="rec-bar-bg"><div class="rec-bar-fill" style="width: ${pct}%;"></div></div>
                        <span class="rec-bar-count">${count}</span>
                    </div>
                `;
            });
            barsContainer.innerHTML = barsHtml;
            
            statusElem.textContent = topCount > 0 ? topCategory : ((rec.key || 'N/A').replace('_', ' ').toUpperCase());
            document.getElementById('rec-mean').textContent = `Score: ${rec.mean ? rec.mean.toFixed(2) : '--'} (1-5)`;

            const fvScale = (v) => v != null ? `$${v.toFixed(2)}` : '--';
            const fvPct = (v) => v != null ? `${(v * 100).toFixed(1)}%` : '--';
            const fvM = (v) => v == null ? '--' : (v / 1e9).toFixed(2);

            const epsBody = document.querySelector('#eps-est-table tbody');
            let epsHtml = '';
            (data.eps_estimates || []).slice(0, 8).forEach(row => {
                let colorKey = 'var(--text-main)';
                let finalVal = fvPct(row.growth);
                if (row.status === 'reported') {
                    colorKey = (row.surprise_pct > 0) ? 'var(--accent)' : (row.surprise_pct < 0 ? 'var(--danger)' : 'var(--text-main)');
                    finalVal = (row.surprise_pct != null) ? fvPct(row.surprise_pct) : '--';
                }
                epsHtml += `<tr><td style="padding: 0.4rem 0;">${row.period}</td><td style="text-align: right; font-weight: 600;">${fvScale(row.avg)}</td><td style="text-align: right; color: ${colorKey};">${finalVal}</td></tr>`;
            });
            epsBody.innerHTML = epsHtml;

            const revBody = document.querySelector('#rev-est-table tbody');
            let revHtml = '';
            (data.rev_estimates || []).slice(0, 8).forEach(row => {
                let colorKey = 'var(--text-main)';
                let finalVal = fvPct(row.growth);
                if (row.status === 'reported') {
                    finalVal = (row.surprise_pct != null) ? fvPct(row.surprise_pct) : '--';
                    if (row.surprise_pct > 0) colorKey = 'var(--accent)';
                    else if (row.surprise_pct < 0) colorKey = 'var(--danger)';
                }
                revHtml += `<tr><td style="padding: 0.4rem 0;">${row.period}</td><td style="text-align: right; font-weight: 600;">${fvM(row.avg)}</td><td style="text-align: right; color: ${colorKey};">${finalVal}</td></tr>`;
            });
            revBody.innerHTML = revHtml;
        } catch (err) {
            console.error("Analyst inline error:", err);
            analystCard.style.display = 'none';
        }
    };

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(`tab-${targetTab}`).classList.add('active');
        });
    });

    const renderWatchlistUI = () => {
        watchlistGrid.innerHTML = '';
        const watchlistHeader = document.getElementById('watchlist-header');

        if (!cachedWatchlistData || cachedWatchlistData.length === 0) {
            emptyWatchlistMsg.style.display = 'block';
            if (watchlistHeader) watchlistHeader.style.display = 'none';
            return;
        }

        emptyWatchlistMsg.style.display = 'none';

        let sortedResults = [...cachedWatchlistData];
        if (!manualOrder) {
            sortedResults.sort((a, b) => {
                const aValid = a.current_price != null && a.fair_value != null;
                const bValid = b.current_price != null && b.fair_value != null;
                if (!aValid && bValid) return 1;
                if (aValid && !bValid) return -1;
                if (!aValid && !bValid) return 0;

                let aVal, bVal;
                if (currentSort.column === 'mos') {
                    aVal = a.margin_of_safety != null ? a.margin_of_safety : -99999;
                    bVal = b.margin_of_safety != null ? b.margin_of_safety : -99999;
                } else if (currentSort.column === 'price') {
                    aVal = a.current_price != null ? a.current_price : 0;
                    bVal = b.current_price != null ? b.current_price : 0;
                } else if (currentSort.column === 'ticker') {
                    aVal = a.ticker; bVal = b.ticker;
                    if (aVal < bVal) return currentSort.order === 'asc' ? -1 : 1;
                    if (aVal > bVal) return currentSort.order === 'asc' ? 1 : -1;
                    return 0;
                }
                return currentSort.order === 'asc' ? aVal - bVal : bVal - aVal;
            });
        }

        if (watchlistHeader) watchlistHeader.style.display = 'flex';

        sortedResults.forEach((data, index) => {
            // Recalculare MOS custom pentru Watchlist
            let customFinalFv = 0;
            let totalW = 0;
            const cw = customWeights; 

            if (data.formula_data?.dcf?.intrinsic_value) { customFinalFv += data.formula_data.dcf.intrinsic_value * cw.dcf; totalW += cw.dcf; }
            if (data.formula_data?.peter_lynch?.fair_value_pe_20) { customFinalFv += data.formula_data.peter_lynch.fair_value_pe_20 * cw.lynch; totalW += cw.lynch; }
            if (data.relative_value) { customFinalFv += data.relative_value * cw.relative; totalW += cw.relative; }
            if (data.formula_data?.peg?.fair_value) { customFinalFv += data.formula_data.peg.fair_value * cw.peg; totalW += cw.peg; }

            let customMos = null;
            if (totalW > 0 && data.current_price) {
                customFinalFv = customFinalFv / totalW;
                customMos = ((customFinalFv - data.current_price) / customFinalFv) * 100;
                data.fair_value = customFinalFv;
                data.margin_of_safety = customMos;
            }

            let dynamicBuyScore = data.buy_score;
            if (data.buy_breakdown && customMos != null) {
                let mosItem = data.buy_breakdown.find(i => i.name.includes("Margin of Safety"));
                if (mosItem) {
                    let newPts = 0;
                    if (customMos > 30.0) newPts = 30;
                    else if (customMos >= 15.0) newPts = 20;
                    else if (customMos >= 0.0) newPts = 10;
                    const oldPts = mosItem.points;
                    mosItem.points = newPts;
                    mosItem.value = `${customMos.toFixed(1)}%`;
                    if (typeof dynamicBuyScore === 'number') {
                        dynamicBuyScore = dynamicBuyScore - oldPts + newPts;
                    }
                }
            }
            
            // Build the card HTML
            // Check for user overrides (server-synced)
            const ov = cachedOverrides[data.ticker];
            const hasOverride = ov && ov.computed && ov.computed.fair_value != null;
            const displayFv = hasOverride ? ov.computed.fair_value : data.fair_value;
            const displayMos = hasOverride ? ov.computed.margin_of_safety : data.margin_of_safety;
            const fvStr = displayFv != null ? formatCurrency(displayFv) + (hasOverride ? ' ✏️' : '') : 'N/A';
            const mosStr = displayMos != null ? formatPercent(displayMos) : 'N/A';
            const mosColor = displayMos > 0 ? 'var(--accent)' : (displayMos < 0 ? 'var(--danger)' : 'var(--text-muted)');
            
            const card = document.createElement('div');
            card.className = 'watchlist-item glass-card';
            card.innerHTML = `
                <div class="drag-handle" style="cursor: grab; color: var(--text-muted); font-size: 1.2rem; padding-right: 0.5rem;">☰</div>
                <div class="watchlist-item-left" style="width: 250px; display: flex; align-items: center; gap: 1rem;">
                    <button class="expand-btn" style="background: none; border: none; color: var(--text-main); font-size: 1.2rem; cursor: pointer; padding: 0;">▶</button>
                    <div>
                        <h3 class="watchlist-ticker" style="margin: 0; font-size: 1.1rem; color: var(--text-main); cursor: pointer;">${data.ticker}</h3>
                        <p style="margin: 0; font-size: 0.85rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px;">${data.name}</p>
                    </div>
                </div>
                
                <div class="watchlist-item-right" style="display: flex; align-items: center; justify-content: flex-end; gap: 3rem; flex-grow: 1;">
                    <div class="col-price" style="width: 100px; text-align: right; font-weight: 600;">${formatCurrency(data.current_price)}</div>
                    <div class="col-fv" style="width: 160px; text-align: right; font-weight: 600;">${fvStr}</div>
                    <div class="col-mos" style="width: 160px; text-align: right; font-weight: 700; color: ${mosColor};">${mosStr}</div>
                </div>
                
                <div class="watchlist-scores-container" style="width: 200px; padding: 0 1rem; margin-left: 2rem; display: flex; align-items: center; justify-content: space-around; gap: 10px;">
                    <div class="mini-score-circle ${dynamicBuyScore >= 76 ? 'mini-score-green' : (dynamicBuyScore >= 41 ? 'mini-score-yellow' : 'mini-score-red')}" title="Buy Score">${dynamicBuyScore || 'N/A'}</div>
                    <div class="mini-score-circle ${(data.health_score || 0) >= 76 ? 'mini-score-green' : ((data.health_score || 0) >= 41 ? 'mini-score-yellow' : 'mini-score-red')}" title="Health Score">${data.health_score || 'N/A'}</div>
                </div>
                
                <div class="watchlist-actions" style="margin-left: 2rem;">
                    <button class="remove-watchlist-btn" data-ticker="${data.ticker}" title="Remove">×</button>
                </div>
            `;
            
            card.querySelector('.watchlist-ticker').addEventListener('click', () => {
                tickerInput.value = data.ticker;
                analyzeTicker(data.ticker);
            });
            
            card.querySelector('.remove-watchlist-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                watchlist = watchlist.filter(t => t !== data.ticker);
                cachedWatchlistData = cachedWatchlistData.filter(d => d.ticker !== data.ticker);
                deleteOverrideFromServer(data.ticker);
                saveWatchlist();
                renderWatchlistUI();
                if (currentTicker === data.ticker) updateWatchlistButtonState();
            });
            
            watchlistGrid.appendChild(card);
        });
    };

    // Event Listeners
    searchBtn.addEventListener('click', analyzeTicker);
    tickerInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') analyzeTicker(); });
    
    logoBtn.addEventListener('click', () => {
        if(currentTicker) {
            watchlistView.style.display = 'none';
            dashboard.style.display = 'block';
        }
    });

    navWatchlistBtn.addEventListener('click', async () => {
        dashboard.style.display = 'none';
        watchlistView.style.display = 'block';
        
        if (!cachedWatchlistData || cachedWatchlistData.length !== watchlist.length) {
            loadingState.style.display = 'flex';
            watchlistView.style.display = 'none';
            cachedWatchlistData = [];
            
            for (const t of watchlist) {
                try {
                    const res = await fetch(`/api/valuation/${t}`);
                    if (res.ok) cachedWatchlistData.push(await res.json());
                } catch (e) {
                    console.error("Failed to load watchlist item", t);
                }
            }
            loadingState.style.display = 'none';
            watchlistView.style.display = 'block';
        }
        
        renderWatchlistUI();
    });

    addToWatchlistBtn.addEventListener('click', toggleWatchlist);

    // ── Bind Modal Close Handlers ──────────────────────────────
    const dataModalEl = document.getElementById('data-modal');
    if (dataModalEl) {
        document.getElementById('close-modal')?.addEventListener('click', (e) => {
            e.stopPropagation();
            dataModalEl.style.display = 'none';
        });
        dataModalEl.addEventListener('click', (e) => {
            if (e.target === dataModalEl) dataModalEl.style.display = 'none';
        });
    }

    const scoreModalEl = document.getElementById('score-modal');
    if (scoreModalEl) {
        document.getElementById('close-score-modal')?.addEventListener('click', (e) => {
            e.stopPropagation();
            scoreModalEl.style.display = 'none';
        });
        scoreModalEl.addEventListener('click', (e) => {
            if (e.target === scoreModalEl) scoreModalEl.style.display = 'none';
        });
    }

    // ── View Data Button Handlers ──────────────────────────────
    document.querySelectorAll('.modal-trigger').forEach(btn => {
        btn.addEventListener('click', () => {
            const model = btn.getAttribute('data-method');
            const modal = document.getElementById('data-modal');
            const body = document.getElementById('modal-body-content');
            const title = document.getElementById('modal-title');
            if (!modal || !body || !currentFormulaData) return;

            let html = '';
            const fmt = (v, decimals = 2) => v != null ? v.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) : 'N/A';
            const fmtPct = (v) => v != null ? (v * 100).toFixed(2) + '%' : 'N/A';
            const fmtBig = (v) => {
                if (v == null) return 'N/A';
                const a = Math.abs(v);
                if (a >= 1e12) return '$' + (v / 1e12).toFixed(2) + 'T';
                if (a >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B';
                if (a >= 1e6) return '$' + (v / 1e6).toFixed(2) + 'M';
                return '$' + v.toLocaleString();
            };

            const fmtBigNum = (v, prefix = '') => {
                if (v == null) return 'N/A';
                const a = Math.abs(v);
                if (a >= 1e12) return prefix + (v / 1e12).toFixed(2) + 'T';
                if (a >= 1e9) return prefix + (v / 1e9).toFixed(2) + 'B';
                if (a >= 1e6) return prefix + (v / 1e6).toFixed(2) + 'M';
                return prefix + v.toLocaleString();
            };

            const row = (label, value) => `<div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.05);"><span style="color:var(--text-muted);">${label}</span><span style="font-weight:600;">${value}</span></div>`;

            if (model === 'dcf' && currentFormulaData.dcf) {
                const d = currentFormulaData.dcf;
                title.textContent = 'Discounted Cash Flow';

                const yearsSourceEl = document.getElementById('dcf-years-source');
                let currentYears = yearsSourceEl ? yearsSourceEl.value : '5yr';
                const renderDCFView = (yp) => {
                    const dataObj = d[yp] || d["5yr"];
                    if (!dataObj) return '<p style="color:var(--text-muted);">Data not available.</p>';
                    
                    const fcfYears = dataObj.fcf_years || [];
                    const sensMatrix = dataObj.sensitivity_matrix || [];
                    const revDcf = dataObj.reverse_dcf_growth;
                    
                    let tableHTML = `<table style="width:100%; border-collapse:collapse; margin-top:20px; font-size: 0.95rem;">
                                        <tr style="border-bottom:1px solid rgba(255,255,255,0.2);"><th style="text-align:left; padding:8px 0; color:white;">Year</th><th style="text-align:right; padding:8px 0; color:white;">Projected FCF</th></tr>`;
                    fcfYears.forEach((val, i) => {
                        tableHTML += `<tr><td style="padding:6px 0; color:white;">Year ${i+1}</td><td style="text-align:right; color:white;">${fmtBig(val)}</td></tr>`;
                    });
                    tableHTML += `</table>`;

                    let matrixHTML = '';
                    if (sensMatrix.length > 0) {
                        matrixHTML = `<div style="margin-top: 25px;">
                            <h4 style="margin-bottom:15px; font-size:1rem; text-transform:uppercase; letter-spacing:1px; color:white; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:5px;">DCF Sensitivity Matrix</h4>
                            <table style="width:100%; border-collapse:collapse; font-size: 0.9rem; text-align:center; background: rgba(0,0,0,0.2); border-radius:6px; overflow:hidden;">`;
                        
                        matrixHTML += `<tr><th style="padding:10px; border:1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05); color:white;">WACC \\ Growth</th>`;
                        const firstRowVals = sensMatrix[0].values;
                        firstRowVals.forEach(v => {
                            matrixHTML += `<th style="padding:10px; border:1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05); color:white;">${fmtPct(v.perpetual_growth)}</th>`;
                        });
                        matrixHTML += `</tr>`;

                        sensMatrix.forEach(row => {
                            matrixHTML += `<tr><th style="padding:10px; border:1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05); color:white;">${fmtPct(row.discount_rate)}</th>`;
                            row.values.forEach(v => {
                                matrixHTML += `<td style="padding:10px; border:1px solid rgba(255,255,255,0.1); color:var(--text-main);">$${fmt(v.fair_value)}</td>`;
                            });
                            matrixHTML += `</tr>`;
                        });
                        matrixHTML += `</table></div>`;
                    }

                    return `
                        <div style="display:flex; justify-content:center; gap:10px; margin-bottom: 20px;">
                            <button class="dcf-toggle-btn ${yp==='5yr'?'active':''}" data-yp="5yr" style="padding:6px 20px; border-radius:20px; border:1px solid var(--accent); background:${yp==='5yr'?'var(--accent)':'transparent'}; color:${yp==='5yr'?'#fff':'var(--accent)'}; cursor:pointer; font-weight:600; font-size:0.9rem; transition: background 0.2s;">5 Years</button>
                            <button class="dcf-toggle-btn ${yp==='10yr'?'active':''}" data-yp="10yr" style="padding:6px 20px; border-radius:20px; border:1px solid var(--accent); background:${yp==='10yr'?'var(--accent)':'transparent'}; color:${yp==='10yr'?'#fff':'var(--accent)'}; cursor:pointer; font-weight:600; font-size:0.9rem; transition: background 0.2s;">10 Years</button>
                        </div>
                        
                        <div style="background:rgba(255,255,255,0.02); padding:20px; border-radius:8px; border:1px solid rgba(255,255,255,0.05); margin-bottom:20px;">
                            <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:var(--text-muted);">Discount Rate (WACC):</span><span style="font-weight:500; color:white;">${fmtPct(d.discount_rate)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:var(--text-muted);">Perpetual Growth Rate:</span><span style="font-weight:500; color:white;">${fmtPct(d.perpetual_growth)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:var(--text-muted);">Shares Outstanding:</span><span style="font-weight:500; color:white;">${d.shares_outstanding ? fmtBigNum(d.shares_outstanding, '') : 'N/A'}</span></div>
                        </div>

                        ${tableHTML}

                        <div style="margin-top:25px; border-top:1px solid rgba(255,255,255,0.1); padding-top:20px;">
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">Total PV of FCFs:</span><span style="font-weight:500; color:white;">${fmtBig(dataObj.sum_pv_cf)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">Terminal Value:</span><span style="font-weight:500; color:white;">${fmtBig(dataObj.terminal_value)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">PV of Terminal Value:</span><span style="font-weight:500; color:white;">${fmtBig(dataObj.pv_terminal_value)}</span></div>
                        </div>

                        <div style="margin-top:25px; border-top:1px solid rgba(255,255,255,0.1); padding-top:20px;">
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">Enterprise Value:</span><span style="font-weight:800; color:white; font-size:1.05rem;">${fmtBig(dataObj.enterprise_value)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">+ Cash & Equivalents:</span><span style="font-weight:600; color:var(--accent);">${fmtBig(dataObj.total_cash)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">- Total Debt:</span><span style="font-weight:600; color:var(--danger);">${fmtBig(dataObj.total_debt)}</span></div>
                        </div>

                        <div style="margin-top:20px; border-top:1px solid rgba(255,255,255,0.1); padding-top:20px;">
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">Equity Value:</span><span style="font-weight:800; color:white; font-size:1.05rem;">${fmtBig(dataObj.equity_value)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:10px 0; margin-top:5px;"><span style="color:var(--text-muted);">Intrinsic Value per Share:</span><span style="font-weight:800; color:var(--accent); font-size:1.15rem;">$${fmt(dataObj.intrinsic_value)}</span></div>
                        </div>

                        <div style="margin-top:25px; display:flex; flex-direction:column; gap:8px;">
                            <span style="color:var(--text-muted); font-size:0.95rem;">Market Implied FCF Growth (Reverse DCF):</span>
                            <span style="font-weight:800; color:var(--accent); font-size:1.2rem;">${fmtPct(revDcf)}</span>
                        </div>

                        ${matrixHTML}
                    `;
                };

                html = renderDCFView(currentYears);
                body.innerHTML = html;
                modal.style.display = 'flex';
                
                const attachToggleEvents = () => {
                    const btns = body.querySelectorAll('.dcf-toggle-btn');
                    btns.forEach(b => {
                        b.addEventListener('click', (e) => {
                            currentYears = e.target.getAttribute('data-yp');
                            const yearsSourceEl = document.getElementById('dcf-years-source');
                            if (yearsSourceEl) {
                                yearsSourceEl.value = currentYears;
                                if (typeof triggerRecalculate === 'function') triggerRecalculate();
                                else if (typeof window.triggerRecalculate === 'function') window.triggerRecalculate();
                            }
                            body.innerHTML = renderDCFView(currentYears);
                            attachToggleEvents();
                        });
                    });
                };
                attachToggleEvents();
                return;
            } else if (model === 'relative' && currentFormulaData.relative) {
                const r = currentFormulaData.relative;
                title.textContent = '📊 Relative Valuation — Data Transparency';
                html = row('Company EPS', '$' + fmt(r.company_eps))
                     + row('Median Peer P/E', r.median_peer_pe ? r.median_peer_pe.toFixed(2) + 'x' : 'N/A')
                     + row('Mean Peer P/E', r.mean_peer_pe ? r.mean_peer_pe.toFixed(2) + 'x' : 'N/A')
                     + row('S&P 500 P/E', r.market_pe_trailing ? r.market_pe_trailing.toFixed(2) + 'x' : 'N/A')
                     + row('Peers Used', (r.peers || []).join(', ') || 'N/A');
            } else if (model === 'peter_lynch' && currentFormulaData.peter_lynch) {
                const p = currentFormulaData.peter_lynch;
                title.textContent = '📊 Forward Multiple — Data Transparency';
                const periodLabel = p.eps_growth_period || 'Est.';
                html = row('Trailing EPS', '$' + fmt(p.trailing_eps))
                     + row(`EPS Growth (${periodLabel})`, fmtPct(p.eps_growth_estimated))
                     + row('Historic P/E (5Y Avg)', p.historic_pe ? p.historic_pe.toFixed(2) + 'x' : 'N/A')
                     + row('Fair Value (PE 20)', '$' + fmt(p.fair_value_pe_20));
            } else if (model === 'peg' && currentFormulaData.peg) {
                const g = currentFormulaData.peg;
                title.textContent = '📊 PEG Valuation — Data Transparency';
                const periodLabel = g.eps_growth_period || 'Est.';
                html = row('Current P/E', g.current_pe ? g.current_pe.toFixed(2) + 'x' : 'N/A')
                     + row(`EPS Growth (${periodLabel})`, fmtPct(g.eps_growth_estimated))
                     + row('Current PEG', g.current_peg ? g.current_peg.toFixed(2) + 'x' : 'N/A')
                     + row('Industry PEG', g.industry_peg ? g.industry_peg.toFixed(2) + 'x' : 'N/A')
                     + row('Fair Value', '$' + fmt(g.fair_value))
                     + row('Margin of Safety', fmtPct(g.margin_of_safety / 100));
            } else {
                title.textContent = 'Data Transparency';
                html = '<p style="color:var(--text-muted);">No data available for this model.</p>';
            }

            body.innerHTML = html;
            modal.style.display = 'flex';
        });
    });

    // ── Score Bar Click Handlers ──────────────────────────────
    function renderScoreBreakdown(title, totalScore, breakdown) {
        const modal = document.getElementById('score-modal');
        const body = document.getElementById('score-modal-body-content');
        const titleEl = document.getElementById('score-modal-title');
        if (!modal || !body) return;

        if (!breakdown || breakdown.length === 0) {
            titleEl.textContent = title;
            body.innerHTML = '<p style="color:var(--text-muted);">No breakdown available.</p>';
            modal.style.display = 'flex';
            return;
        }

        let totalMax = 0;
        breakdown.forEach(item => totalMax += item.max_points || 0);
        const scoreVal = totalScore != null ? totalScore : '?';

        // Build header - Centered score, title on left
        let html = `
            <div style="display:grid; grid-template-columns: 1fr auto 1fr; align-items:center; margin-bottom:20px; padding-right:45px;">
                <h3 style="margin:0; font-size:1.1rem; color:white; font-weight:700;">${title}</h3>
                <div style="text-align:center;">
                    <div style="font-size:0.8rem; color:var(--text-muted);">Total:</div>
                    <div style="font-size:1.4rem; font-weight:800; color:white;">${scoreVal}/${totalMax}</div>
                </div>
                <div></div>
            </div>
        `;

        // Build rows matching user's reference design
        breakdown.forEach(item => {
            const pts = item.points || 0;
            const maxPts = item.max_points || 0;
            const pct = maxPts > 0 ? (pts / maxPts) : 0;

            // Dot color: green if >= 75%, yellow if >= 40%, red otherwise
            let dotColor = 'var(--danger)';
            let ptsColor = 'var(--danger)';
            if (pct >= 0.75) { dotColor = 'var(--accent)'; ptsColor = 'var(--accent)'; }
            else if (pct >= 0.4) { dotColor = '#fbbf24'; ptsColor = '#fbbf24'; }

            html += `
                <div style="display:flex; align-items:center; justify-content:space-between; padding:14px 0; border-top:1px solid rgba(255,255,255,0.06);">
                    <div style="flex:1; min-width:0;">
                        <div style="font-weight:600; font-size:0.9rem; color:white;">${item.name}</div>
                    </div>
                    <div style="font-weight:700; font-size:0.95rem; color:white; min-width:60px; text-align:center;">${item.value || 'N/A'}</div>
                    <div style="display:flex; align-items:center; gap:8px; min-width:90px; justify-content:flex-end;">
                        <span style="width:10px; height:10px; border-radius:50%; background:${dotColor}; display:inline-block; flex-shrink:0;"></span>
                        <span style="font-weight:700; font-size:0.9rem; color:${ptsColor};">${pts}/${maxPts} pts</span>
                    </div>
                </div>
            `;
        });

        if (titleEl) titleEl.textContent = '';
        body.innerHTML = html;
        modal.style.display = 'flex';
    };

});
