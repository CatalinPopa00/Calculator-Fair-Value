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

    const autocompleteList = document.getElementById('autocomplete-list');
    const logoBtn = document.getElementById('logo-btn');
    
    // --- Analyst Tabs Logic ---
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.analyst-tab-btn');
        if (!btn) return;

        const targetTab = btn.getAttribute('data-tab');
        if (!targetTab) return;

        // Update buttons
        document.querySelectorAll('.analyst-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Update contents
        document.querySelectorAll('.analyst-tab-content').forEach(content => {
            if (content.id === `tab-${targetTab}`) {
                content.classList.add('active');
                content.style.display = 'block'; 
            } else {
                content.classList.remove('active');
                if (window.innerWidth <= 768) {
                    content.style.display = 'none';
                } else {
                    content.style.display = ''; 
                }
            }
        });
    });

    // v59: Instant Capitalization & Search Feedback logic
    if (tickerInput) {
        tickerInput.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
            if (this.value.length >= 1) {
                fetchSuggestions(this.value);
            } else {
                autocompleteList.innerHTML = '';
                autocompleteList.style.display = 'none';
            }
        });
        
        tickerInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') analyzeTicker();
        });
    }

    const fetchSuggestions = async (q) => {
        try {
            // v59: Use relative path for production safety
            const res = await fetch(`/api/search/${encodeURIComponent(q)}`);
            if (res.ok) {
                const results = await res.json();
                populateAutocomplete(results);
            }
        } catch (e) { console.error('Autocomplete fetch failed:', e); }
    };

    const populateAutocomplete = (items) => {
        autocompleteList.innerHTML = '';
        if (!items || items.length === 0) {
            autocompleteList.style.display = 'none';
            return;
        }
        
        items.slice(0, 8).forEach(item => {
            const div = document.createElement('div');
            div.className = 'autocomplete-item';
            div.style.cssText = 'padding: 10px 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.05); color: white; display: flex; justify-content: space-between;';
            div.innerHTML = `
                <span style="font-weight: bold; color: var(--accent);">${item.ticker}</span>
                <span style="font-size: 0.85em; color: var(--text-muted); text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 200px;">${item.name}</span>
            `;
            div.onclick = () => {
                tickerInput.value = item.ticker;
                autocompleteList.style.display = 'none';
                analyzeTicker(item.ticker);
            };
            autocompleteList.appendChild(div);
        });
        autocompleteList.style.display = 'block';
    };

    // Close autocomplete on outside click
    document.addEventListener('click', (e) => {
        if (!tickerInput.contains(e.target) && !autocompleteList.contains(e.target)) {
            autocompleteList.style.display = 'none';
        }
    });

    let currentFormulaData = null;
    let currentTicker = null;
    let currentHealthBreakdown = null;
    let currentBuyBreakdown = null;
    let currentPiotroskiBreakdown = null;
    let chartRevFcf = null;
    let chartEpsShares = null;
    let globalData = null; 
    let _originalPrice = null; // Stores the real (API) price before simulation
    let _simulating = false;

    // --- SIMULATE PRICE ENGINE ---
    const initSimulatePrice = () => {
        const btn = document.getElementById('simulate-price-btn');
        const input = document.getElementById('simulate-price-input');
        const label = document.getElementById('simulate-price-label');
        const priceEl = document.getElementById('current-price');
        if (!btn || !input) return;

        btn.onclick = () => {
            _simulating = !_simulating;
            if (_simulating) {
                // Activate simulation mode
                _originalPrice = globalData ? globalData.current_price : 0;
                input.value = _originalPrice.toFixed(2);
                input.style.display = 'block';
                priceEl.style.display = 'none';
                label.style.display = 'block';
                btn.classList.add('active');
                btn.title = 'Reset to real price';
                input.focus();
                input.select();
            } else {
                // Deactivate: restore original price
                input.style.display = 'none';
                priceEl.style.display = '';
                label.style.display = 'none';
                btn.classList.remove('active');
                btn.title = 'Simulate a different price';
                if (globalData && _originalPrice != null) {
                    globalData.current_price = _originalPrice;
                    priceEl.textContent = formatCurrency(_originalPrice);
                    recalcWithSimPrice(_originalPrice);
                }
            }
        };

        input.oninput = () => {
            const val = parseFloat(input.value);
            if (isNaN(val) || val <= 0 || !globalData) return;
            globalData.current_price = val;
            recalcWithSimPrice(val);
        };
    };

    const recalcWithSimPrice = (simPrice) => {
        if (!globalData) return;
        const prof = globalData.company_profile;
        if (!prof) return;

        // --- 1. Recalculate dependent metrics ---
        const eps = prof.trailing_eps || 0;
        const shares = prof.shares_outstanding || 0;
        const fairValue = globalData.fair_value;
        const revenue = prof.revenue || 0;
        const totalCash = prof.total_cash || 0;
        const totalDebt = prof.total_debt || 0;
        const ebitda = prof.ebitda || 0;
        const bookValuePerShare = prof.price_to_book && _originalPrice ? (_originalPrice / prof.price_to_book) : 0;
        const dividendRate = prof.dividend_rate || 0;
        const pe5y = prof.historic_pe || 0;

        // Margin of Safety
        const newMos = fairValue ? ((fairValue - simPrice) / simPrice) * 100 : null;

        // P/E Ratio (Trailing TTM)
        const newPE = (eps > 0) ? simPrice / eps : 0;

        // P/S Ratio
        const newPS = (revenue > 0 && shares > 0) ? simPrice / (revenue / shares) : 0;

        // Market Cap
        const newMktCap = simPrice * shares;

        // EV / EBITDA
        const ev = newMktCap + totalDebt - totalCash;
        const newEvEbitda = (ebitda > 0) ? ev / ebitda : 0;

        // Price-to-Book
        const newPB = (bookValuePerShare > 0) ? simPrice / bookValuePerShare : 0;

        // Dividend Yield
        const newDivYield = (simPrice > 0 && dividendRate > 0) ? (dividendRate / simPrice) : 0;

        // --- 2. Update Profile Table (reactive) ---
        const pBody = document.getElementById('profile-body');
        if (pBody) {
            // Update P/E (Trailing TTM) row
            const rows = pBody.querySelectorAll('tr');
            rows.forEach(row => {
                const label = row.querySelector('.profile-label');
                const val = row.querySelector('.profile-value');
                if (!label || !val) return;
                const txt = label.textContent.trim();
                if (txt === 'P/E (Trailing TTM)') {
                    val.textContent = newPE > 0 ? newPE.toFixed(2) + 'x' : 'N/A';
                    val.style.color = _simulating ? '#fbbf24' : '';
                } else if (txt === 'Market Cap') {
                    val.textContent = formatBigNumber(newMktCap, '$');
                    val.style.color = _simulating ? '#fbbf24' : '';
                }
            });
        }

        // --- 3. Update Price display ---
        const priceEl = document.getElementById('current-price');
        if (priceEl && !_simulating) {
            priceEl.textContent = formatCurrency(simPrice);
        }

        // --- 4. Recalculate Good to Buy scoring locally ---
        if (currentBuyBreakdown) {
            let totalDelta = 0;

            currentBuyBreakdown.forEach(item => {
                const oldPts = item.points_awarded || 0;
                let newPts = oldPts; // default: keep
                const metric = item.metric || '';

                if (metric === 'P/E Ratio') {
                    // Hybrid blended scoring (absolute + relative)
                    const isFin = prof.sector && prof.sector.toLowerCase().includes('financial');
                    let ptsAbs = 0, ptsRel = 0;
                    if (isFin) {
                        ptsAbs = (newPE > 0 && newPE < 10) ? 7.5 : ((newPE > 0 && newPE <= 15) ? 3.75 : 0);
                        if (newPE > 0 && pe5y > 0) {
                            const diff = ((newPE - pe5y) / pe5y) * 100;
                            ptsRel = diff < -15 ? 7.5 : (Math.abs(diff) <= 15 ? 3.75 : 0);
                        }
                    } else {
                        ptsAbs = (newPE > 0 && newPE < 15) ? 10 : ((newPE > 0 && newPE <= 25) ? 5 : 0);
                        if (newPE > 0 && pe5y > 0) {
                            const diff = ((newPE - pe5y) / pe5y) * 100;
                            ptsRel = diff < -15 ? 10 : (Math.abs(diff) <= 15 ? 5 : 0);
                        }
                    }
                    newPts = Math.min(ptsAbs + ptsRel, item.max_points);
                    item.value = newPE > 0 ? newPE.toFixed(2) + 'x' : '0.00x';
                } else if (metric === 'P/S Ratio') {
                    newPts = (newPS > 0 && newPS < 4) ? 10 : ((newPS > 0 && newPS <= 8) ? 5 : 0);
                    newPts = Math.min(newPts, item.max_points);
                    item.value = newPS > 0 ? newPS.toFixed(2) + 'x' : '0.00x';
                } else if (metric === 'EV / EBITDA') {
                    newPts = (newEvEbitda > 0 && newEvEbitda < 12) ? 10 : ((newEvEbitda > 0 && newEvEbitda <= 18) ? 5 : 0);
                    newPts = Math.min(newPts, item.max_points);
                    item.value = newEvEbitda > 0 ? newEvEbitda.toFixed(2) + 'x' : '0.00x';
                } else if (metric === 'Price-to-Book') {
                    newPts = (newPB > 0 && newPB < 1.2) ? 15 : ((newPB > 0 && newPB <= 2.0) ? 7.5 : 0);
                    newPts = Math.min(newPts, item.max_points);
                    item.value = newPB > 0 ? newPB.toFixed(2) + 'x' : '0.00x';
                } else if (metric === 'Dividend Yield') {
                    const dyPct = newDivYield * 100;
                    const isFin = prof.sector && prof.sector.toLowerCase().includes('financial');
                    if (isFin) {
                        newPts = dyPct > 4 ? 15 : (dyPct >= 2 ? 7.5 : 0);
                    } else {
                        // REITs or others with Dividend Yield in buy
                        newPts = dyPct > 5 ? 15 : (dyPct >= 3 ? 7.5 : 0);
                    }
                    newPts = Math.min(newPts, item.max_points);
                    item.value = dyPct.toFixed(1) + '%';
                }

                item.points_awarded = newPts;
            });
            // Score UI updating and summation will be reliably handled by updateInsightsAndScores
            // via the window.triggerRecalculate() call at the end of this function.
        }

        // Let window.triggerRecalculate() handle Fair Value and MoS display dynamically
        if(window.triggerRecalculate) {
            window.triggerRecalculate();
        }

        // --- 6. Update strengths/risks ---
        const allMetrics = [...(currentHealthBreakdown || []), ...(currentBuyBreakdown || [])];
        const strengths = allMetrics.filter(m => m.points_awarded === m.max_points && m.max_points > 0);
        strengths.sort((a, b) => b.max_points - a.max_points);
        const risks = allMetrics.filter(m => m.points_awarded === 0 && m.max_points > 0);
        risks.sort((a, b) => b.max_points - a.max_points);

        const strengthsList = document.getElementById('top-strengths-list');
        if (strengthsList) {
            strengthsList.innerHTML = '';
            strengths.slice(0, 3).forEach(s => {
                const li = document.createElement('li');
                li.textContent = `${s.metric}: ${s.value}`;
                strengthsList.appendChild(li);
            });
        }
        const risksList = document.getElementById('risk-factors-list');
        if (risksList) {
            risksList.innerHTML = '';
            risks.slice(0, 3).forEach(r => {
                const li = document.createElement('li');
                li.textContent = `${r.metric}: ${r.value}`;
                risksList.appendChild(li);
            });
        }
    };

    // Custom Weights Logic (v34: Now ticker-specific via overrides)
    let customWeights = { dcf: 25, peg: 25, relative: 25, lynch: 25 }; 

    // Watchlist State 
    let watchlist = JSON.parse(localStorage.getItem('fairValueWatchlist')) || [];
    
    // Non-destructive Watchlist Merge (v37: Fixed sync-back loop and added error protection)
    fetch('/api/watchlist?t=' + new Date().getTime(), { cache: 'no-store' })
        .then(r => {
            if (!r.ok) throw new Error('Watchlist sync unreachable');
            return r.json();
        })
        .then(serverData => {
            if (Array.isArray(serverData)) {
                const localData = JSON.parse(localStorage.getItem('fairValueWatchlist')) || [];
                // Combine both and remove duplicates
                const combined = [...new Set([...localData, ...serverData])];
                
                const hasChanged = JSON.stringify(watchlist) !== JSON.stringify(combined);
                watchlist = combined;
                localStorage.setItem('fairValueWatchlist', JSON.stringify(watchlist));
                
                // v37: If we merged new data, sync it back to server so other devices get it too
                if (hasChanged) {
                    fetch('/api/watchlist', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tickers: watchlist })
                    }).catch(e => console.error('Sync-back failed:', e));
                }
                
                // v38: Always trigger an initial background fetch for watchlist data to ensure scores are sync'd
                if (watchlist.length > 0) {
                    refreshWatchlistData();
                }
            }
        })
        .catch(err => {
            console.error('Watchlist sync error (aborting merge to protect local data):', err);
            // v37: On error, we keep 'watchlist' as loaded from localStorage (Line 38) 
            // and do NOT sync back to the server.
        });

    // Overrides State (loaded from server on init)
    let cachedOverrides = {};
    let overrideSaveTimer = null;

    // Load overrides from server on startup
    fetch('/api/overrides?t=' + Date.now(), { cache: 'no-store' }).then(r => r.json()).then(data => {
        cachedOverrides = data || {};
    }).catch(() => { cachedOverrides = {}; });

    const getSmartWeights = (sector) => {
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
        return w;
    };
    window.getSmartWeights = getSmartWeights;

    const getActiveToggles = (ticker) => {
        const ov = (cachedOverrides && cachedOverrides[ticker]) ? cachedOverrides[ticker] : {};
        return ov.toggles || {
            'toggle-dcf': true,
            'toggle-peter_lynch': true,
            'toggle-relative': true,
            'toggle-peg': true,
            'toggle-multiple': false
        };
    };
    window.getActiveToggles = getActiveToggles;

    const setSmartWeights = (sector) => {
        const w = getSmartWeights(sector);
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

    // UPDATED: Sync both MOS and PEG to the Score Breakdown dynamically (moved to top-level)
    const updateInsightsAndScores = (newMos, newPeg) => {
        if (!currentBuyBreakdown || !globalData) return;

        // Update Margin of Safety
        let mosItem = currentBuyBreakdown.find(i => i.metric && i.metric.includes("Margin of Safety"));
        if (mosItem) {
            let pts = 0;
            let mos_str = "N/A";
            if (newMos != null) {
                mos_str = `${newMos.toFixed(1)}%`;
                if (newMos > 20.0) pts = 30;
                else if (newMos >= 0.0) pts = 15;
            }

            mosItem.points_awarded = pts;
            mosItem.value = mos_str;
        }

        // Update Custom PEG
        let pegItem = currentBuyBreakdown.find(i => i.metric && i.metric.includes("PEG Ratio"));
        if (pegItem && newPeg != null) {
            let pts = 0;
            let peg_str = `${newPeg.toFixed(2)}x`;
            
            if (newPeg < 1.2 && newPeg > 0) pts = 10;
            else if (newPeg <= 2.0 && newPeg > 0) pts = 5;
            
            pegItem.points_awarded = pts;
            pegItem.value = peg_str;
        }

        if (typeof globalData.good_to_buy_total === 'number') {
            const rawTotal = currentBuyBreakdown.reduce((sum, item) => sum + (item.points_awarded || 0), 0);
            globalData.good_to_buy_total = Math.min(Math.max(rawTotal, 0), 100);
            updateScoreUI(globalData.good_to_buy_total, 'buy-score-circle', 'buy-score-fill');
        }

        const allMetrics = [...(currentHealthBreakdown || []), ...(currentBuyBreakdown || [])];
        const strengths = allMetrics.filter(m => m.points_awarded === m.max_points && m.max_points > 0);
        strengths.sort((a, b) => b.max_points - a.max_points);
        const topStrengths = strengths.slice(0, 3);

        const risks = allMetrics.filter(m => m.points_awarded === 0 || (m.max_points > 0 && m.points_awarded <= (m.max_points / 3)));
        risks.sort((a, b) => (a.points_awarded / a.max_points) - (b.points_awarded / b.max_points));
        const topRisks = risks.slice(0, 3);

        const strengthsList = document.getElementById('top-strengths-list');
        if (strengthsList) {
            strengthsList.innerHTML = '';
            if (topStrengths.length > 0) {
                topStrengths.forEach(s => {
                    const li = document.createElement('li');
                    li.innerHTML = `<strong>${s.metric.split(' (')[0]}:</strong> ${s.value}`;
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
                    li.innerHTML = `<strong>${r.metric.split(' (')[0]}:</strong> ${r.value}`;
                    risksList.appendChild(li);
                });
            } else {
                risksList.innerHTML = '<li>No critical risks detected.</li>';
            }
        }
    };

    const calcLocalDcf = (fcf, growth, wacc, perp, shares, cash, debt, buybackRate = 0, years = 5, exitMult = 10.0) => {
        if (!fcf || !shares || shares <= 0) return null;
        
        // WACC Smart Cap
        const finalWacc = Math.max(0.07, Math.min(wacc, 0.105));
        
        let pv = 0;
        let f = fcf;
        for (let i = 1; i <= years; i++) {
            f *= (1 + growth);
            pv += f / Math.pow(1 + finalWacc, i);
        }
        
        const method = document.getElementById('dcf-method-selector')?.value || 'perpetual';
        let tv = 0;
        if (method === 'perpetual') {
            tv = (f * (1 + perp)) / (finalWacc - perp);
        } else {
            tv = f * exitMult;
        }
        
        const pvTv = tv / Math.pow(1 + finalWacc, years);
        const ev = pv + pvTv;
        const eqVal = ev + (cash || 0) - (debt || 0);
        if (eqVal <= 0) return null;
        const effectiveShares = shares * Math.pow(1 - (buybackRate || 0), years);
        return eqVal / (effectiveShares > 0 ? effectiveShares : shares);
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
            saveOverride(currentTicker); // Persist immediately when "Auto-Set" is clicked
            if(typeof window.triggerRecalculate === 'function') {
                window.triggerRecalculate();
            }
        });

        document.getElementById('save-weights-btn').addEventListener('click', () => {
            customWeights.dcf = parseFloat(document.getElementById('weight-dcf').value) || 0;
            customWeights.peg = parseFloat(document.getElementById('weight-peg').value) || 0;
            customWeights.relative = parseFloat(document.getElementById('weight-relative').value) || 0;
            customWeights.lynch = parseFloat(document.getElementById('weight-lynch').value) || 0;
            
            saveOverride(currentTicker); // Save to ticker-specific overrides
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
            margin: prof.operating_margin,
            rev_growth: prof.revenue_growth,
            eps_growth: prof.earnings_growth
        };
        
        const competitors = prof.competitor_metrics || [];
        const all = [mainComp, ...competitors];
        
        const fmtPE = (v) => v != null ? v.toFixed(2) + 'x' : 'N/A';
        const fmtEPS = (v) => v != null ? '$' + v.toFixed(2) : 'N/A';
        const fmtMargin = (v) => v != null ? (v * 100).toFixed(2) + '%' : 'N/A';
        const fmtPctRow = (v) => v != null ? (v * 100).toFixed(2) + '%' : 'N/A';

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
                    ${all.map(c => `<td style="padding:12px; text-align:right; font-weight:bold;">${fmtMargin(c.margin || c.operating_margin)}</td>`).join('')}
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding:12px; color:var(--text-muted);">Revenue Growth (y/y)</td>
                    ${all.map(c => {
                        const val = (c.rev_growth != null ? c.rev_growth : c.revenue_growth);
                        let color = 'inherit';
                        if (val > 0) color = 'var(--accent)';
                        else if (val < 0) color = 'var(--danger)';
                        return `<td style="padding:12px; text-align:right; font-weight:bold; color:${color};">${fmtPctRow(val)}</td>`;
                    }).join('')}
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding:12px; color:var(--text-muted);">EPS Growth (y/y)</td>
                    ${all.map(c => {
                        const val = (c.eps_growth != null ? c.eps_growth : c.earnings_growth);
                        let color = 'inherit';
                        if (val > 0) color = 'var(--accent)';
                        else if (val < 0) color = 'var(--danger)';
                        return `<td style="padding:12px; text-align:right; font-weight:bold; color:${color};">${fmtPctRow(val)}</td>`;
                    }).join('')}
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); background: rgba(56, 189, 248, 0.03);">
                    <td style="padding:12px; color:var(--accent); font-weight:bold;">Piotroski F-Score</td>
                    ${all.map((c, i) => {
                        const val = i === 0 ? (globalData ? globalData.piotroski_score : 'N/A') : (c.piotroski_score || '—');
                        let color = 'var(--text-muted)';
                        if (val !== 'N/A' && val !== '—') {
                            color = val >= 7 ? 'var(--accent)' : (val >= 4 ? '#fbbf24' : 'var(--danger)');
                        }
                        return `<td style="padding:12px; text-align:right; font-weight:800; color:${color};">${val}${val !== 'N/A' && val !== '—' ? '/9' : ''}</td>`;
                    }).join('')}
                </tr>
            </tbody>
        </table>`;
        
        container.innerHTML = html;
        document.getElementById('comparison-modal').style.display = 'flex';
        document.body.style.overflow = 'hidden';
    };

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

    // ── Piotroski F-Score UI ──────────────────────────────────────────────────
    const updatePiotroskiUI = (scoreVal) => {
        const circle = document.getElementById('piotroski-score-circle');
        const fill   = document.getElementById('piotroski-score-fill');
        const badge  = document.getElementById('piotroski-label-badge');
        if (!circle || !fill) return;

        // Reset classes
        circle.className = 'score-circle';
        fill.className = 'score-bar-fill';
        circle.style.color = '';
        fill.style.backgroundColor = '';
        fill.style.width = '0%';

        if (scoreVal === 'N/A' || scoreVal == null) {
            circle.textContent = 'N/A';
            circle.style.color = 'var(--text-muted)';
            fill.style.backgroundColor = 'var(--text-muted)';
            if (badge) { badge.textContent = '--'; badge.style.background = 'rgba(148,163,184,0.2)'; badge.style.color = 'var(--text-muted)'; }
            return;
        }

        const num = parseInt(scoreVal);
        circle.textContent = num;
        // Bar width based on /9 scale
        const barPct = Math.round((num / 9) * 100);
        setTimeout(() => { fill.style.width = `${barPct}%`; }, 50);

        if (num >= 7) {
            circle.classList.add('score-green');
            fill.classList.add('bg-score-green');
            if (badge) { badge.textContent = 'Strong'; badge.style.background = 'rgba(16,185,129,0.25)'; badge.style.color = 'var(--accent)'; }
        } else if (num >= 4) {
            circle.classList.add('score-yellow');
            fill.classList.add('bg-score-yellow');
            if (badge) { badge.textContent = 'Neutral'; badge.style.background = 'rgba(251,191,36,0.2)'; badge.style.color = '#fbbf24'; }
        } else {
            circle.classList.add('score-red');
            fill.classList.add('bg-score-red');
            if (badge) { badge.textContent = 'Weak'; badge.style.background = 'rgba(239,68,68,0.2)'; badge.style.color = 'var(--danger)'; }
        }
    };

    const renderPiotroskiBreakdown = (score, breakdown) => {
        const modalEl = document.getElementById('score-modal');
        const bodyEl  = document.getElementById('score-modal-body-content');
        if (!modalEl || !bodyEl) return;

        const num = (score === 'N/A' || score == null) ? null : parseInt(score);
        const labelColor = num == null ? '#94a3b8' : (num >= 7 ? 'var(--accent)' : num >= 4 ? '#fbbf24' : 'var(--danger)');
        const labelText  = num == null ? 'N/A' : (num >= 7 ? 'Strong' : num >= 4 ? 'Neutral' : 'Weak');

        const groups = ['Profitability', 'Leverage & Liquidity', 'Operating Efficiency'];
        const groupIcons = { 'Profitability': '📈', 'Leverage & Liquidity': '🏦', 'Operating Efficiency': '⚙️' };

        let html = `
            <div style="text-align:center; margin-bottom: 1.5rem;">
                <h3 style="font-size: 1.2rem; margin: 0 0 0.5rem; color: white;">Piotroski F-Score Breakdown</h3>
                <div style="font-size: 2.8rem; font-weight: 800; color: ${labelColor}; line-height: 1;">${num != null ? num : 'N/A'}<span style="font-size: 1.2rem; color: var(--text-muted); font-weight: 500;">/9</span></div>
                <div style="font-size: 0.9rem; font-weight: 700; color: ${labelColor}; margin-top: 4px;">${labelText}</div>
                <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 8px; max-width: 380px; margin-left: auto; margin-right: auto;">
                    Score ≥ 7 = Strong financial health &nbsp;|&nbsp; 4-6 = Neutral &nbsp;|&nbsp; ≤ 3 = Weak
                </p>
            </div>`;

        if (!breakdown || breakdown.length === 0) {
            html += `<p style="color: var(--text-muted); text-align: center;">No breakdown data available.</p>`;
        } else {
            groups.forEach(group => {
                const items = breakdown.filter(b => b.group === group);
                if (!items.length) return;
                html += `
                    <div style="margin-bottom: 1.2rem;">
                        <h4 style="font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.6rem; border-bottom: 1px solid rgba(255,255,255,0.07); padding-bottom: 6px;">
                            ${groupIcons[group] || ''} ${group}
                        </h4>`;
                items.forEach(item => {
                    const passed = item.passed;
                    const icon   = passed === null ? '⬜' : (passed ? '✅' : '❌');
                    const rowColor = passed === null ? 'var(--text-muted)' : (passed ? 'var(--accent)' : 'var(--danger)');
                    html += `
                        <div style="display:flex; align-items:flex-start; gap:10px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
                            <span style="font-size:1.1rem; min-width:22px;">${icon}</span>
                            <div style="flex:1; min-width:0;">
                                <div style="font-size:0.85rem; font-weight:700; color:white;">${item.criterion}</div>
                                <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">${item.description}</div>
                                ${item.value && item.value !== 'N/A' ? `<div style="font-size:0.78rem; color:${rowColor}; margin-top:3px; font-weight:600;">${item.value}</div>` : ''}
                            </div>
                            <span style="font-size:0.85rem; font-weight:700; color:${passed === null ? 'var(--text-muted)' : rowColor}; min-width:28px; text-align:right;">
                                ${passed === null ? '—' : (passed ? '+1' : '0')}
                            </span>
                        </div>`;
                });
                html += `</div>`;
            });
        }

        bodyEl.innerHTML = html;
        modalEl.style.display = 'flex';

        // Close button
        const closeBtn = document.getElementById('close-score-modal');
        if (closeBtn) closeBtn.onclick = () => { modalEl.style.display = 'none'; };
        modalEl.onclick = (e) => { if (e.target === modalEl) modalEl.style.display = 'none'; };
    };

    const updateFairValue = () => {
        if (!currentFormulaData || !globalData) return;
        const prof = globalData.company_profile;
        const dcfCardMos = document.getElementById('dcf-card-mos');

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
                    const rawVal = document.getElementById('dcf-custom-buyback').value;
                    buybackRate = (rawVal === '' || isNaN(parseFloat(rawVal))) ? 0 : parseFloat(rawVal) / 100;
                }

                const baseFcf = currentFormulaData.dcf.fcf;
                const shares = prof.shares_outstanding;
                
                // Dynamic WACC and Perpetual Growth from backend
                const w = currentFormulaData.dcf.discount_rate || 0.09;
                const p = currentFormulaData.dcf.perpetual_growth || 0.02;

                if (fcfSource === 'analyst') {
                    const waccInput = document.getElementById('dcf-custom-wacc');
                    const backendWacc = currentFormulaData.dcf.discount_rate_applied / 100;
                    const method = document.getElementById('dcf-method-selector')?.value || 'perpetual';
                    
                    // v161: Robust null check for dcfData to prevent "Cannot read properties of null"
                    if (dcfData) {
                        const branch = method === 'multiple' ? dcfData.dcf_exit_multiple : dcfData.dcf_perpetual;
                        
                    // SYNC v62: Use backend branch if no manual overrides affecting calc are present
                    if (buybackRate === 0 && (!waccInput || !waccInput.value) && fcfSource !== 'custom') {
                        // Use the exact same branch selection as the modal to ensure sync
                        dcfVal = branch ? branch.fair_value_per_share : null;
                    }
                    
                    // Fallback to local calculation only if backend branch failed or overrides are present
                    if (dcfVal === null) {
                        const g = currentFormulaData.dcf.eps_growth_applied || 0.10;
                        const wAnalyst = (waccInput && waccInput.value) ? parseFloat(waccInput.value)/100 : w;
                        const em = parseFloat(document.getElementById('input-exit-multiple')?.value) || (globalData.dcf_assumptions?.recommended_exit_multiple || 15.0);
                        dcfVal = calcLocalDcf(baseFcf, g, wAnalyst, p, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years, em);
                    }
                }

            } else if (fcfSource === 'historical') {
                const hg = prof.historic_fcf_growth != null ? prof.historic_fcf_growth : 0.05;
                const em = parseFloat(document.getElementById('input-exit-multiple')?.value) || (data.dcf_assumptions?.recommended_exit_multiple || 10.0);
                dcfVal = calcLocalDcf(baseFcf, hg, w, p, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years, em);
            } else if (fcfSource === 'eps_growth') {
                const g = currentFormulaData.dcf.eps_growth_applied || 0.10;
                const em = parseFloat(document.getElementById('input-exit-multiple')?.value) || (data.dcf_assumptions?.recommended_exit_multiple || 10.0);
                dcfVal = calcLocalDcf(baseFcf, g, w, p, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years, em);
            } else if (fcfSource === 'custom') {
                const gRaw = document.getElementById('dcf-custom-growth').value;
                const wRaw = document.getElementById('dcf-custom-wacc').value;
                const pRaw = document.getElementById('dcf-custom-perp').value;
                const emRaw = document.getElementById('input-exit-multiple').value;
                
                const g = (gRaw === '' || isNaN(parseFloat(gRaw))) ? 0.15 : parseFloat(gRaw) / 100;
                const wCustom = (wRaw === '' || isNaN(parseFloat(wRaw))) ? 0.09 : parseFloat(wRaw) / 100;
                const pCustom = (pRaw === '' || isNaN(parseFloat(pRaw))) ? 0.025 : parseFloat(pRaw) / 100;
                const em = (emRaw === '' || isNaN(parseFloat(emRaw))) ? (data.dcf_assumptions?.recommended_exit_multiple || 10.0) : parseFloat(emRaw);
                
                dcfVal = calcLocalDcf(baseFcf, g, wCustom, pCustom, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years, em);
            }
        }
        setValuationStatus(dcfVal, globalData.current_price, 'dcf-status', 'dcf-value');
        
        if (dcfVal != null && dcfCardMos) {
            const currentDcfMos = ((dcfVal - globalData.current_price) / globalData.current_price) * 100;
            dcfCardMos.textContent = `MOS: ${formatPercent(currentDcfMos)}`;
            dcfCardMos.style.color = currentDcfMos > 0 ? 'var(--accent)' : 'var(--danger)';
        }

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
                const rawG = document.getElementById('peg-custom-growth').value;
                usedGrowth = (rawG === '' || isNaN(parseFloat(rawG))) ? 0.20 : parseFloat(rawG) / 100;
            }

            const eps = globalData.company_profile.trailing_eps || 0;
            const currentPe = (eps > 0) ? (globalData.current_price / eps) : (currentFormulaData.peg.current_pe || (parseFloat(globalData.company_profile.trailing_pe) || 0));
            // v61: Default to 1.25 if industry_peg is missing (e.g. no peers found)
            const industryPeg = currentFormulaData.peg.industry_peg || 1.25;

            if (usedGrowth > 0 && currentPe > 0 && industryPeg > 0) {
                currentPegToDisplay = currentPe / (usedGrowth * 100);
                pegVal = globalData.current_price * (industryPeg / currentPegToDisplay);
                pegMos = ((pegVal - globalData.current_price) / globalData.current_price) * 100;
            } else if (pegSrc === 'analyst') {
                pegVal = currentFormulaData.peg.fair_value;
                currentPegToDisplay = currentFormulaData.peg.current_peg;
                if (pegVal != null) {
                    pegMos = ((pegVal - globalData.current_price) / globalData.current_price) * 100;
                }
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
                    
                    // Also sync to the new card-mos element for consistency with other cards
                    const pegCardMos = document.getElementById('peg-card-mos');
                    if (pegCardMos) {
                        pegCardMos.textContent = `MOS: ${formatPercent(pegMos)}`;
                        pegCardMos.style.color = pegMos > 0 ? 'var(--accent)' : 'var(--danger)';
                        pegCardMos.style.display = 'block';
                    }
                }

                if (globalData.current_price < pegVal) {
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
                const rawG = document.getElementById('lynch-custom-growth').value;
                usedGrowth = (rawG === '' || isNaN(parseFloat(rawG))) ? 0.20 : parseFloat(rawG) / 100;
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
                // v46: Simple Future Project (no discounting per user preference)
                lynchVal = targetEps * selectedMult;
            }
        }

        setValuationStatus(lynchVal, globalData.current_price, 'lynch-status', 'lynch-fair-value');
        
        const lynchCardMos = document.getElementById('lynch-card-mos');
        if (lynchCardMos && lynchVal != null) {
            const lynchMos = ((lynchVal - globalData.current_price) / globalData.current_price) * 100;
            lynchCardMos.textContent = `MOS: ${formatPercent(lynchMos)}`;
            lynchCardMos.style.color = lynchMos > 0 ? 'var(--accent)' : 'var(--danger)';
            lynchCardMos.style.display = 'block';
        } else if (lynchCardMos) {
            lynchCardMos.style.display = 'none';
        }

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
        setValuationStatus(relVal, globalData.current_price, 'relative-status', 'relative-value');
        
        const relCardMos = document.getElementById('relative-card-mos');
        if (relCardMos && relVal != null) {
            const relMos = ((relVal - globalData.current_price) / globalData.current_price) * 100;
            relCardMos.textContent = `MOS: ${formatPercent(relMos)}`;
            relCardMos.style.color = relMos > 0 ? 'var(--accent)' : 'var(--danger)';
            relCardMos.style.display = 'block';
        } else if (relCardMos) {
            relCardMos.style.display = 'none';
        }
        
        // --- CALCULATE FINAL FAIR VALUE ---
        const hasUserWeights = localStorage.getItem('fairValueWeights') !== null;
        const modelsToggled = !document.getElementById('toggle-peter_lynch').checked || 
                             !document.getElementById('toggle-peg').checked || 
                             !document.getElementById('toggle-relative').checked || 
                             !document.getElementById('toggle-dcf').checked;

        let finalFv = globalData.fair_value;
        let finalMos = globalData.margin_of_safety;

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
                finalMos = ((finalFv - globalData.current_price) / globalData.current_price) * 100;
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
        'fcf-source', 'dcf-years-source', 'dcf-method-selector', 'input-exit-multiple', 'dcf-custom-growth', 'dcf-custom-wacc', 'dcf-custom-perp',
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

    document.querySelectorAll('.valuation-toggle').forEach(toggle => {
        toggle.onchange = updateAndSave;
    });

    const analyzeTicker = async (queryParam) => {
        // v40: Instant UI feedback - Switch to loading state IMMEDIATELY
        autocompleteList.style.display = 'none';
        watchlistView.style.display = 'none';
        dashboard.style.display = 'none';
        loadingState.style.display = 'flex';
        
        // v59: Update button text to show progress
        if (searchBtn) {
            searchBtn.disabled = true;
            searchBtn.textContent = 'Analyzing...';
        }
        
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // Force flush any pending saves before clearing the DOM
        if (overrideSaveTimer && pendingOverrideTicker) {
            clearTimeout(overrideSaveTimer);
            saveOverridesToServer(pendingOverrideTicker, pendingOverridePayload);
        }

        let query = (queryParam && typeof queryParam === 'string') ? queryParam : tickerInput.value.trim();
        if (!query) {
            loadingState.style.display = 'none';
            return;
        }

        // Optimization: If it's a direct ticker from watchlist or autocomplete, SKIP server-side resolution
        if (!queryParam) {
            try {
                const searchRes = await fetch(`/api/search/${encodeURIComponent(query)}`);
                if (searchRes.ok) {
                    const results = await searchRes.json();
                    if (results && results.length > 0) {
                        if (results[0].ticker.toUpperCase() !== query.toUpperCase() || query.length > 5 || query.includes(' ')) {
                            query = results[0].ticker;
                            tickerInput.value = query;
                        }
                    }
                }
            } catch (e) {
                console.warn('[Search] Resolution failed, proceeding with literal query:', e);
            }
        }

        // Reset inputs to clean state...
        ['fcf-source', 'lynch-eps-source', 'peg-eps-source'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = 'analyst';
        });

        try {
            const response = await fetch(`/api/valuation/${encodeURIComponent(query)}?t=${Date.now()}`);
            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();
            displayData(data);

        } catch (error) {
            console.error('Error fetching valuation:', error);
            alert('Error: ' + error.message + '\nStack: ' + error.stack);
            loadingState.style.display = 'none';
        } finally {
            if (searchBtn) {
                searchBtn.disabled = false;
                searchBtn.textContent = 'Analyze';
            }
        }
    };

    const formatCurrency = (val) => val != null ? `$${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'N/A';
    const formatPercent = (val) => val != null ? `${val.toFixed(2)}%` : '0%';

    const displayData = (data) => {
        globalData = data; 
        currentFormulaData = data.formula_data;
        currentTicker = data.ticker;

        // Ticker-Specific Weights Logic (v34)
        const override = cachedOverrides[data.ticker] || {};
        if (override.weights) {
            // Restore saved weights for this specific company
            customWeights = { ...override.weights };
        } else if (data.company_profile && data.company_profile.sector) {
            // No saved weights -> Auto-Set by Sector and SAVE immediately
            customWeights = setSmartWeights(data.company_profile.sector);
            saveOverride(data.ticker); 
        }

        elements.name.textContent = data.name;
        elements.ticker.textContent = data.ticker;
        elements.currentPrice.textContent = formatCurrency(data.current_price);

        // Reset Simulate Price mode on new ticker load
        _simulating = false;
        _originalPrice = data.current_price;
        const simInput = document.getElementById('simulate-price-input');
        const simBtn = document.getElementById('simulate-price-btn');
        const simLabel = document.getElementById('simulate-price-label');
        if (simInput) simInput.style.display = 'none';
        if (simBtn) { simBtn.classList.remove('active'); simBtn.title = 'Simulate a different price'; }
        if (simLabel) simLabel.style.display = 'none';
        elements.currentPrice.style.display = '';
        initSimulatePrice();

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
                fvContainer.insertAdjacentHTML('afterend', `
                    <div id="company-desc-card" class="glass-card" style="margin-top: 15px; padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <h3 style="font-size: 0.85rem; color: var(--text-muted); margin: 0; text-transform: uppercase; letter-spacing: 1px;">Company Overview</h3>
                            <div id="ai-synthesis-badge" style="display: none; background: linear-gradient(135deg, #38bdf8, #818cf8); color: white; font-size: 0.65rem; padding: 4px 10px; border-radius: 20px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">✨ A.I. Sinteză</div>
                        </div>
                        <div id="company-desc-text" style="font-size: 0.95rem; line-height: 1.7; color: white; max-height: 250px; overflow-y: auto; text-align: justify; padding-right: 8px;"></div>
                    </div>`);
                descCard = document.getElementById('company-desc-card');
            }
            
            const descText = document.getElementById('company-desc-text');
            const aiBadge = document.getElementById('ai-synthesis-badge');
            
            if (data.company_overview_synthesis) {
                descText.textContent = data.company_overview_synthesis;
                aiBadge.style.display = 'block';
                descCard.style.borderLeft = '4px solid #38bdf8';
            } else {
                descText.textContent = (data.company_profile && data.company_profile.business_summary) || 'Description not available.';
                aiBadge.style.display = 'none';
                descCard.style.borderLeft = 'none';
            }
        }

        updateWatchlistButtonState();

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

        currentHealthBreakdown = data.health_breakdown;
        currentBuyBreakdown = data.buy_breakdown;

        updateScoreUI(data.health_score_total, 'health-score-circle', 'health-score-fill');
        updateScoreUI(data.good_to_buy_total, 'buy-score-circle', 'buy-score-fill');

        // Bind click handlers on score rows (must be done here, after data is loaded)
        const healthRow = document.getElementById('health-score-row') || document.getElementById('health-score-circle')?.closest('.score-row');
        console.log('[Score Handlers] healthRow:', healthRow, 'breakdown:', currentHealthBreakdown?.length);
        if (healthRow) {
            healthRow.style.cursor = 'pointer';
            healthRow.onclick = function() {
                console.log('[Score Click] Health clicked!');
                renderScoreBreakdown('Company Health Breakdown', data.health_score_total, currentHealthBreakdown);
            };
        }
        const buyRow = document.getElementById('buy-score-row') || document.getElementById('buy-score-circle')?.closest('.score-row');
        console.log('[Score Handlers] buyRow:', buyRow, 'breakdown:', currentBuyBreakdown?.length);
        if (buyRow) {
            buyRow.style.cursor = 'pointer';
            buyRow.onclick = function() {
                console.log('[Score Click] Buy clicked!');
                renderScoreBreakdown('Good to Buy Score Breakdown', data.good_to_buy_total, currentBuyBreakdown);
            };
        }

        // Piotroski F-Score UI
        currentPiotroskiBreakdown = data.piotroski_breakdown;
        updatePiotroskiUI(data.piotroski_score);
        const piotroskiRow = document.getElementById('piotroski-score-row');
        if (piotroskiRow) {
            piotroskiRow.style.cursor = 'pointer';
            piotroskiRow.onclick = function() {
                renderPiotroskiBreakdown(data.piotroski_score, currentPiotroskiBreakdown);
            };
        }

        // UPDATED: Sync both MOS and PEG to the Score Breakdown dynamically

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
                <tr><td class="profile-label">P/E (Trailing TTM)</td><td class="profile-value">${(data.current_price && prof.trailing_eps) ? (data.current_price / prof.trailing_eps).toFixed(2) + 'x' : 'N/A'}</td></tr>
                <tr><td class="profile-label">P/E (5Y Avg)</td><td class="profile-value">${prof.historic_pe ? prof.historic_pe.toFixed(2) + 'x' : 'N/A'}</td></tr>
                <tr><td class="profile-label">EPS (Trailing TTM)</td><td class="profile-value">${prof.trailing_eps ? '$' + prof.trailing_eps.toFixed(2) : 'N/A'}</td></tr>
                ${(prof.adjusted_eps && Math.abs(prof.adjusted_eps - prof.trailing_eps) > 0.1) ? 
                    `<tr><td class="profile-label" style="color:var(--accent);">EPS (Adjusted TTM)</td><td class="profile-value" style="color:var(--accent); font-weight:bold;">$${prof.adjusted_eps.toFixed(2)}</td></tr>` : ''}
                <tr><td class="profile-label">Debt-to-Equity</td><td class="profile-value">${prof.debt_to_equity != null ? prof.debt_to_equity.toFixed(2) + 'x' : 'N/A'}</td></tr>
                <tr><td class="profile-label">Insider Ownership</td><td class="profile-value">${formatSafePct(prof.insider_ownership)}</td></tr>
                <tr><td class="profile-label">Shares Out.</td><td class="profile-value">${formatBigNumber(prof.shares_outstanding, '')}</td></tr>
                <tr><td class="profile-label">${prof.buyback_rate < 0 ? 'Dilution rate' : 'Buyback rate'}</td><td class="profile-value" style="color: ${prof.buyback_rate < 0 ? '#ef4444' : 'inherit'}">${prof.buyback_rate != null ? (prof.buyback_rate > 0 ? '+' : '') + formatSafePct(prof.buyback_rate) : 'N/A'}</td></tr>
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

        // --- ADDITIONAL SECTIONS ---
        renderAnalystEstimatesInline(data.ticker);

                // v44: Transposed Table with Sparklines
                const config = [
                    { label: 'Year', key: 'year', isHeader: true },
                    { label: 'Revenue (B)', key: 'revenue_b', formatter: v => v.toFixed(2) + ' B', sparkKey: 'revenue_b' },
                    { label: 'EPS (Adj)', key: 'eps', formatter: v => '$' + v.toFixed(2), sparkKey: 'eps' },
                    { label: 'FCF (B)', key: 'fcf_b', formatter: v => v.toFixed(2) + ' B', sparkKey: 'fcf_b' },
                    { label: 'Net Margin', key: 'net_margin_pct', formatter: v => v, sparkKey: 'net_margin_pct' },
                    { label: 'Cash (B)', key: 'cash_b', formatter: v => v.toFixed(2) + ' B', sparkKey: 'cash_b' },
                    { label: 'Debt (B)', key: 'total_debt_b', formatter: v => v.toFixed(2) + ' B', sparkKey: 'total_debt_b' },
                    { label: 'Shares (B)', key: 'shares_out_b', formatter: v => v.toFixed(2) + ' B', sparkKey: 'shares_out_b' },
                    { label: 'ROIC', key: 'roic_pct', formatter: v => v, sparkKey: 'roic_pct' }
                ];

                const generateSparkline = (values) => {
                    if (!values || values.length < 2) return '';
                    const cleanValues = values.map(v => {
                        if (typeof v === 'string') return parseFloat(v.replace(/[^0-9.-]/g, '')) || 0;
                        return v || 0;
                    });
                    const min = Math.min(...cleanValues);
                    const max = Math.max(...cleanValues);
                    const range = (max - min) || 1;
                    const w = 40, h = 15;
                    const pts = cleanValues.map((v, i) => `${(i/(cleanValues.length-1))*w},${h - ((v-min)/range)*h}`).join(' ');
                    const color = cleanValues[cleanValues.length-1] >= cleanValues[0] ? '#10b981' : '#ef4444';
                    return `<svg width="${w}" height="${h}" style="vertical-align:middle;margin-left:auto;"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>`;
                };

                let tableHtml = '';
                config.forEach(metric => {
                    const isYear = metric.key === 'year';
                    const sparkHtml = !isYear ? generateSparkline(anchors.map(a => a[metric.key])) : '';
                    
                    tableHtml += `<tr>`;
                    tableHtml += `
                        <td class="sticky-col" style="background: var(--card-bg); padding: 12px 16px; border-right: 1px solid rgba(255,255,255,0.05); min-width: 160px;">
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span style="font-weight: 700; color: var(--text-muted); text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px;">${metric.label}</span>
                                ${sparkHtml}
                            </div>
                        </td>`;
                    
                    anchors.forEach(yearData => {
                        const val = yearData[metric.key];
                        let displayVal = metric.formatter ? metric.formatter(val) : val;
                        const cellStyle = isYear ? 'color: var(--primary); font-weight: 800; font-size: 0.95rem;' : 'color: white; font-weight: 600; font-size: 0.9rem;';
                        tableHtml += `<td style="padding: 12px 20px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.03); min-width: 90px; ${cellStyle}">${displayVal}</td>`;
                    });
                    tableHtml += `</tr>`;
                });
                
                trendsBody.innerHTML = tableHtml;
                document.getElementById('trends-scroll-wrapper').classList.add('transposed-view');
            } else {
                trendsBody.innerHTML = '<tr><td style="text-align: center; color: var(--text-muted); padding: 2rem;">No historical anchors available.</td></tr>';
            }
        }

        loadingState.style.display = 'none';
        watchlistView.style.display = 'none';
        dashboard.style.display = 'block';

        renderAnalystEstimatesInline(data.ticker);
        renderHistoricalCharts(data);

        // Sync DCF Exit Multiple from backend assumptions
        const exitMultipleInput = document.getElementById('input-exit-multiple');
        if (exitMultipleInput && data.dcf_assumptions) {
            exitMultipleInput.value = data.dcf_assumptions.recommended_exit_multiple || 10.0;
        }
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
        'fcf-source', 'dcf-years-source', 'dcf-method-selector', 'input-exit-multiple',
        'dcf-custom-growth', 'dcf-custom-wacc', 'dcf-custom-perp',
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

    const getComputedValues = () => {
        const fvText = elements.fairValue.textContent;
        if (fvText === 'N/A') return {};
        const fvMatch = fvText.match(/[\-0-9.,]+/);
        const fv = fvMatch ? parseFloat(fvMatch[0].replace(/,/g, '')) : null;

        const mosText = elements.marginSafety.textContent;
        const mosMatch = mosText.match(/([\-0-9.]+)%/);
        const mos = mosMatch ? parseFloat(mosMatch[1]) : null;
        
        const hScoreEl = document.getElementById('health-score-circle');
        const bScoreEl = document.getElementById('buy-score-circle');
        const pScoreEl = document.getElementById('piotroski-score-circle');
        const hScore = hScoreEl ? parseInt(hScoreEl.textContent) : null;
        const bScore = bScoreEl ? parseInt(bScoreEl.textContent) : null;
        const pScore = pScoreEl ? parseInt(pScoreEl.textContent) : null;
        
        return { 
            fair_value: fv, 
            margin_of_safety: mos,
            health_score: hScore,
            buy_score: bScore,
            piotroski_score: pScore
        };
    };

    let pendingOverridePayload = null;
    let pendingOverrideTicker = null;

    const saveOverridesToServer = (ticker, payloadObj = null) => {
        if (!ticker || !watchlist.includes(ticker)) return;
        
        const payload = payloadObj || {
            ticker: ticker,
            inputs: collectOverrideInputs(),
            toggles: collectOverrideToggles(),
            computed: getComputedValues(),
            weights: customWeights
        };

        cachedOverrides[ticker] = payload;

        fetch('/api/overrides', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).catch(err => console.error('Override sync error:', err));
        
        pendingOverridePayload = null;
        pendingOverrideTicker = null;
    };

    const saveOverridesDebounced = (ticker) => {
        if (!ticker || !watchlist.includes(ticker)) return;
        
        // Take synchronous snapshot BEFORE potential fast-navigation clears DOM
        pendingOverridePayload = {
            ticker: ticker,
            inputs: collectOverrideInputs(),
            toggles: collectOverrideToggles(),
            computed: getComputedValues(),
            weights: { ...customWeights }
        };
        pendingOverrideTicker = ticker;
        
        cachedOverrides[ticker] = pendingOverridePayload; // Optimistic local UI update

        if (overrideSaveTimer) clearTimeout(overrideSaveTimer);
        overrideSaveTimer = setTimeout(() => {
            if (pendingOverrideTicker === ticker && pendingOverridePayload) {
                saveOverridesToServer(ticker, pendingOverridePayload);
            }
        }, 500);
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
                if (id === 'dcf-method-selector') {
                    switchDCFMethod(val);
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

    const saveOverride = (ticker) => {
        if (!ticker) return;
        saveOverridesToServer(ticker);
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

    const switchDCFMethod = (method) => {
        const rowPerp = document.getElementById('row-input-perpetual');
        const rowExit = document.getElementById('row-input-exit-multiple');
        if (method === 'multiple') {
            if (rowPerp) rowPerp.style.display = 'none';
            if (rowExit) rowExit.style.display = 'flex';
        } else {
            if (rowPerp) rowPerp.style.display = 'flex';
            if (rowExit) rowExit.style.display = 'none';
        }
        updateFairValue();
    };
    window.switchDCFMethod = switchDCFMethod;

    const dcfMethodSelector = document.getElementById('dcf-method-selector');
    if (dcfMethodSelector) {
        dcfMethodSelector.addEventListener('change', (e) => {
            switchDCFMethod(e.target.value);
            saveOverridesDebounced(currentTicker);
        });
    }

    // UNIVERSAL PERSISTENCE: Attach listeners to ALL override-able components (v62)
    overrideInputIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                updateFairValue();
                saveOverridesDebounced(currentTicker);
            });
            // Also listen for input on number/text fields for immediate feedback
            if (el.tagName === 'INPUT') {
                el.addEventListener('input', () => {
                    updateFairValue();
                    saveOverridesDebounced(currentTicker);
                });
            }
        }
    });

    overrideToggleIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                updateFairValue();
                saveOverridesDebounced(currentTicker);
            });
        }
    });

    // INITIALIZATION: Default to Perpetual
    switchDCFMethod('perpetual');

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

        // ── Chart 1: Revenue & FCF (Bar chart, billions) ──
        const ctxRevFcf = document.getElementById('chart-rev-fcf');
        if (ctxRevFcf) {
            if (chartRevFcf) chartRevFcf.destroy();
            chartRevFcf = new Chart(ctxRevFcf, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'Revenue ($B)',
                            data: hd.revenue.map(v => v ? +(v / 1e9).toFixed(2) : 0),
                            backgroundColor: bgColors('rgba(56, 189, 248, 1)', 0.7, 0.3),
                            borderColor: 'rgba(56, 189, 248, 1)',
                            borderWidth: 1,
                            borderRadius: 4,
                            order: 2
                        },
                        {
                            label: 'FCF ($B)',
                            data: hd.fcf.map(v => v ? +(v / 1e9).toFixed(2) : 0),
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
                        y: { ticks: { color: '#94a3b8', callback: v => '$' + v.toLocaleString() + 'B' }, grid: { color: 'rgba(148,163,184,0.1)' } }
                    }
                }
            });
        }

        // ── Chart 2: EPS & Shares Outstanding (Dual Axis) ──
        const ctxEps = document.getElementById('chart-eps-shares');
        if (ctxEps) {
            if (chartEpsShares) chartEpsShares.destroy();

            const epsData = hd.eps || [];
            const sharesData = (hd.shares || []).map(v => v ? +(v / 1e9).toFixed(3) : 0);

            chartEpsShares = new Chart(ctxEps, {
                type: 'bar', // Base type remains bar for the background
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'Shares (B)',
                            data: sharesData,
                            backgroundColor: bgColors('rgba(251, 191, 36, 1)', 0.4, 0.2),
                            borderColor: 'rgba(251, 191, 36, 1)',
                            borderWidth: 1,
                            borderRadius: 4,
                            yAxisID: 'y1',
                            order: 2
                        },
                        {
                            label: 'EPS ($)',
                            data: epsData.map(v => v ? +v.toFixed(2) : 0),
                            type: 'line',
                            borderColor: 'rgba(168, 85, 247, 1)',
                            backgroundColor: 'rgba(168, 85, 247, 0.1)',
                            pointBackgroundColor: 'rgba(168, 85, 247, 1)',
                            pointBorderColor: '#fff',
                            pointRadius: 5,
                            pointHoverRadius: 7,
                            borderWidth: 3,
                            fill: false,
                            tension: 0.3,
                            segment: {
                                borderDash: ctx => labels[ctx.p1DataIndex] && String(labels[ctx.p1DataIndex]).includes('Est') ? [6, 4] : undefined
                            },
                            yAxisID: 'y',
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
                        y1: { position: 'right', ticks: { color: '#fbbf24', callback: v => v + 'B' }, grid: { drawOnChartArea: false }, title: { display: true, text: 'Shares (B)', color: '#fbbf24' } }
                    }
                }
            });
        }
    };

    const renderAnalystEstimatesInline = async (ticker) => {
        const analystCard = document.getElementById('analyst-estimates-card');
        if (!ticker || !analystCard) return;
        
        analystCard.style.setProperty('display', 'block', 'important');
        document.getElementById('pt-avg').textContent = '...';
        document.getElementById('rec-status').textContent = '...';
        document.querySelector('#eps-est-table tbody').innerHTML = '';
        document.querySelector('#rev-est-table tbody').innerHTML = '';

        try {
            const res = await fetch(`/api/analyst/${ticker}?t=${Date.now()}`);
            if (!res.ok) throw new Error('API Error');
            const data = await res.json();
            console.log("ANALYST API DATA RECEIVED:", data);

            if (data.error) throw new Error(data.error);

            const pt = data.price_target || {};
            if (document.getElementById('pt-avg')) document.getElementById('pt-avg').textContent = (pt.avg && typeof pt.avg === 'number') ? `$${pt.avg.toFixed(2)}` : '--';
            if (document.getElementById('pt-upside')) {
                const ups = pt.upside_pct;
                document.getElementById('pt-upside').textContent = (ups && typeof ups === 'number') ? `${ups > 0 ? '+' : ''}${ups.toFixed(1)}%` : '--';
                document.getElementById('pt-upside').style.color = (ups > 0) ? 'var(--accent)' : (ups < 0 ? 'var(--danger)' : 'var(--text-muted)');
            }
            if (document.getElementById('pt-low')) document.getElementById('pt-low').textContent = (pt.low && typeof pt.low === 'number') ? `$${pt.low.toFixed(2)}` : '--';
            if (document.getElementById('pt-high')) document.getElementById('pt-high').textContent = (pt.high && typeof pt.high === 'number') ? `$${pt.high.toFixed(2)}` : '--';

            const rec = data.recommendation || {};
            const statusElem = document.getElementById('rec-status');
            const counts = rec.counts || {};
            const maxVal = Math.max(...Object.values(counts), 1);
            const barsContainer = document.getElementById('rec-bars');
            barsContainer.innerHTML = '';

            const labels = { strongBuy: 'SB', buy: 'B', hold: 'H', sell: 'S', strongSell: 'SS' };
            
            ['strongBuy', 'buy', 'hold', 'sell', 'strongSell'].forEach(k => {
                const count = counts[k] || 0;
                const pct = (count / maxVal) * 100;
                barsContainer.innerHTML += `
                    <div style="display:flex; align-items:center; gap:8px; font-size:0.7rem; color:var(--text-muted); margin-bottom:2px;">
                        <span style="width:20px;">${labels[k]}</span>
                        <div style="flex:1; height:4px; background:rgba(255,255,255,0.05); border-radius:2px; overflow:hidden;">
                            <div style="width:${pct}%; height:100%; background:var(--accent);"></div>
                        </div>
                        <span style="width:15px; text-align:right;">${count}</span>
                    </div>
                `;
            });

            if (statusElem) {
                const medianRating = rec.median_label || 'N/A';
                statusElem.textContent = medianRating;
                
                // Color based on sentiment score (0-100)
                const sent = rec.sentiment || 0;
                if (sent >= 66) statusElem.style.color = '#4ade80'; // Green
                else if (sent >= 45) statusElem.style.color = '#fbbf24'; // Yellow
                else statusElem.style.color = '#f87171'; // Red
            }

            if (document.getElementById('rec-mean')) {
                const sent = rec.sentiment || 0;
                document.getElementById('rec-mean').textContent = `Sentiment: ${sent.toFixed(1)}/100`;
            }

            // Tables population
            const eBody = document.querySelector('#eps-est-table tbody');
            const rBody = document.querySelector('#rev-est-table tbody');
            if (eBody) eBody.innerHTML = '';
            if (rBody) rBody.innerHTML = '';

            const getColor = (item) => {
                if (item.status !== 'reported') return 'var(--text-main)'; // neutral for estimates
                
                // For reported: color based on surprise if available, otherwise growth
                const surprise = item.surprise_pct || 0;
                if (surprise > 0) return '#4ade80'; // Beat
                if (surprise < 0) return '#f87171'; // Miss
                
                // Fallback to growth if surprise is missing but it's reported
                if (item.growth > 0) return '#4ade80';
                if (item.growth < 0) return '#f87171';
                
                return 'var(--text-main)';
            };

            const eItems = data.eps_estimates || [];
            eItems.slice(0, 8).forEach(item => {
                if (!item) return;
                const pLabel = item.period || '--';
                const aVal = (item.avg != null) ? '$' + parseFloat(item.avg).toFixed(2) : '--';
                let gVal = '--';
                
                if (item.status === 'reported' && item.surprise_pct != null) {
                    gVal = (parseFloat(item.surprise_pct) * 100).toFixed(1) + '%';
                } else if (item.growth != null) {
                    gVal = (parseFloat(item.growth) * 100).toFixed(1) + '%';
                }
                
                const sColor = getColor(item);
                const weight = item.status === 'reported' ? 'bold' : 'normal';
                if (eBody) eBody.innerHTML += `<tr><td style="padding:4px 0;${item.status === 'reported' ? 'color:#4ade80;' : ''}">${pLabel}</td><td style="text-align:right;">${aVal}</td><td style="text-align:right;color:${sColor};font-weight:${weight};">${gVal}</td></tr>`;
            });

            const rItems = data.rev_estimates || [];
            rItems.slice(0, 8).forEach(item => {
                if (!item) return;
                const pLabel = item.period || '--';
                const aVal = (item.avg != null) ? (parseFloat(item.avg) / 1e9).toFixed(2) + 'B' : '--';
                const gVal = (item.growth != null) ? (parseFloat(item.growth) * 100).toFixed(1) + '%' : '--';
                
                const sColor = getColor(item);
                const weight = item.status === 'reported' ? 'bold' : 'normal';
                if (rBody) rBody.innerHTML += `<tr><td style="padding:4px 0;${item.status === 'reported' ? 'color:#4ade80;' : ''}">${pLabel}</td><td style="text-align:right;">${aVal}</td><td style="text-align:right;color:${sColor};font-weight:${weight};">${gVal}</td></tr>`;
            });

            // v70: Reactive Chart Updates - Link Analyst Projections to the main Stability Chart
            // This ensures that even if the primary valuation fetch has stale or missing projections,
            // the chart updates as soon as the fresher Analyst Consensus data arrives.
            if ((chartEpsShares || chartRevFcf) && (eItems.length > 0 || rItems.length > 0)) {
                console.log("[Analyst] Synchronizing projections to historical charts...");
                
                // 1. Sync EPS (Chart 2)
                if (chartEpsShares && eItems.length > 0) {
                    const labels = chartEpsShares.data.labels;
                    const epsDs = chartEpsShares.data.datasets.find(d => d.label === 'EPS ($)');
                    const sharesDs = chartEpsShares.data.datasets.find(d => d.label === 'Shares (B)');
                    if (epsDs) {
                        let updated = false;
                        eItems.forEach(item => {
                            if (item.status === 'estimate') {
                                const yrMatch = item.period.match(/\d{4}/);
                                if (yrMatch) {
                                    const yearStr = yrMatch[0];
                                    const idx = labels.findIndex(l => String(l).includes(yearStr) && String(l).includes('Est'));
                                    if (idx !== -1 && item.avg != null) {
                                        epsDs.data[idx] = +parseFloat(item.avg).toFixed(2);
                                        // If shares are missing for estimates (often are), carry over the last known actual
                                        if (sharesDs && (sharesDs.data[idx] === 0 || sharesDs.data[idx] == null)) {
                                            const lastActualIdx = labels.findLastIndex(l => !String(l).includes('Est'));
                                            if (lastActualIdx !== -1) sharesDs.data[idx] = sharesDs.data[lastActualIdx];
                                        }
                                        updated = true;
                                    }
                                }
                            }
                        });
                        if (updated) chartEpsShares.update('none');
                    }
                }
                
                // 2. Sync Revenue (Chart 1)
                if (chartRevFcf && rItems.length > 0) {
                    const labels = chartRevFcf.data.labels;
                    const revDs = chartRevFcf.data.datasets.find(d => d.label === 'Revenue ($B)');
                    const fcfDs = chartRevFcf.data.datasets.find(d => d.label === 'FCF ($B)');
                    if (revDs) {
                        let updated = false;
                        rItems.forEach(item => {
                            if (item.status === 'estimate') {
                                const yrMatch = item.period.match(/\d{4}/);
                                if (yrMatch) {
                                    const yearStr = yrMatch[0];
                                    const idx = labels.findIndex(l => String(l).includes(yearStr) && String(l).includes('Est'));
                                    if (idx !== -1 && item.avg != null) {
                                        const oldVal = revDs.data[idx];
                                        const newVal = +(parseFloat(item.avg) / 1e9).toFixed(2);
                                        
                                        // Update revenue
                                        revDs.data[idx] = newVal;
                                        
                                        // Update FCF if it's missing or zero using the last known margin
                                        if (fcfDs && (fcfDs.data[idx] === 0 || fcfDs.data[idx] == null)) {
                                            const lastActualIdx = labels.findLastIndex(l => !String(l).includes('Est'));
                                            if (lastActualIdx !== -1 && revDs.data[lastActualIdx] > 0) {
                                                const margin = fcfDs.data[lastActualIdx] / revDs.data[lastActualIdx];
                                                fcfDs.data[idx] = +(newVal * margin).toFixed(2);
                                            }
                                        }
                                        updated = true;
                                    }
                                }
                            }
                        });
                        if (updated) chartRevFcf.update('none');
                    }
                }
            }
        } catch (err) {
            console.error("Analyst major error:", err);
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
        try {
            if (!watchlistGrid) {
                console.error("watchlistGrid element not found!");
                return;
            }
            watchlistGrid.innerHTML = '';

            if (!watchlist || watchlist.length === 0) {
                emptyWatchlistMsg.style.display = 'block';
                return;
            }

            emptyWatchlistMsg.style.display = 'none';

            if (!Array.isArray(cachedWatchlistData)) {
                cachedWatchlistData = [];
            }

            // Map watchlist tickers to data
            let augmentedData = watchlist.map(t => {
                const tickerUpper = t.toUpperCase();
                const found = (cachedWatchlistData || []).find(d => d && d.ticker && d.ticker.toUpperCase() === tickerUpper);
                if (found) return { ...found };
                
                // If not found in cache, check if it's currently in flight
                const isLoading = window._watchlistFetching && window._watchlistFetching.has(tickerUpper);
                return { 
                    ticker: t, 
                    name: isLoading ? 'Loading...' : 'Data Unavailable', 
                    current_price: null, 
                    fair_value: null, 
                    margin_of_safety: null, 
                    health_score_total: null, 
                    good_to_buy_total: null,
                    is_loading: isLoading
                };
            });

            // Sort
            if (!manualOrder) {
                augmentedData.sort((a, b) => {
                    if (!a || !b) return 0;
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
                    } else if (currentSort.column === 'health') {
                        aVal = a.health_score_total != null ? a.health_score_total : -99999;
                        bVal = b.health_score_total != null ? b.health_score_total : -99999;
                    } else if (currentSort.column === 'buy') {
                        aVal = a.good_to_buy_total != null ? a.good_to_buy_total : -99999;
                        bVal = b.good_to_buy_total != null ? b.good_to_buy_total : -99999;
                    } else if (currentSort.column === 'ticker') {
                        aVal = a.ticker || ''; bVal = b.ticker || '';
                        if (aVal < bVal) return currentSort.order === 'asc' ? -1 : 1;
                        if (aVal > bVal) return currentSort.order === 'asc' ? 1 : -1;
                        return 0;
                    }
                    return currentSort.order === 'asc' ? aVal - bVal : bVal - aVal;
                });
            }

            // Render loop
            augmentedData.forEach((data) => {
                if (!data || !data.ticker) return;
                try {
                    const toggles = getActiveToggles(data.ticker);
                    // Use server-provided values for consistency
                    const globalOv = cachedOverrides[data.ticker] || data.overrides;
                    const hasOverride = globalOv && globalOv.computed && globalOv.computed.fair_value != null;
                    
                    const displayFv = hasOverride ? globalOv.computed.fair_value : data.fair_value;
                    const displayMos = (displayFv != null && data.current_price) ? ((displayFv - data.current_price) / data.current_price) * 100 : data.margin_of_safety;
                    const displayHealth = (globalOv && globalOv.computed && globalOv.computed.health_score_total != null) ? globalOv.computed.health_score_total : data.health_score_total;
                    
                    // buy score sync logic
                    const dynamicBuyScore = data.good_to_buy_total;
                    let displayBuy = (globalOv && globalOv.computed && globalOv.computed.good_to_buy_total != null) ? globalOv.computed.good_to_buy_total : dynamicBuyScore;
                    
                    const fvStr = displayFv != null ? formatCurrency(displayFv) : 'N/A';
                    const mosStr = displayMos != null ? formatPercent(displayMos) : 'N/A';
                    const mosColor = displayMos > 0 ? 'var(--accent)' : (displayMos < 0 ? 'var(--danger)' : 'var(--text-muted)');
                    const dotClass = (displayBuy || 0) >= 76 ? 'dot-green' : ((displayBuy || 0) >= 41 ? 'dot-yellow' : 'dot-red');
                    const hDotClass = (displayHealth || 0) >= 76 ? 'dot-green' : ((displayHealth || 0) >= 41 ? 'dot-yellow' : 'dot-red');

                    const card = document.createElement('div');
                    card.className = `watchlist-card-new ${data.is_loading ? 'wl-loading-state' : ''}`;
                    
                    const loadingSpinner = `<div class="wl-spinner"></div>`;
                    
                    card.innerHTML = `
                        <button class="wl-close-btn" data-ticker="${data.ticker}">&times;</button>
                        <div class="wl-header">
                            <h3 class="wl-ticker">${data.ticker}</h3>
                            <p class="wl-name">${data.is_loading ? 'Fetching latest data...' : data.name}</p>
                        </div>
                        <div class="wl-metrics-bar">
                            <div class="wl-metric-item">
                                <span class="wl-m-label">Price</span>
                                <span class="wl-m-value">${data.is_loading ? loadingSpinner : formatCurrency(data.current_price)}</span>
                            </div>
                            <div class="wl-metric-item">
                                <span class="wl-m-label">Fair Val ${hasOverride ? '✏️' : ''}</span>
                                <span class="wl-m-value">${data.is_loading ? loadingSpinner : fvStr}</span>
                            </div>
                            <div class="wl-metric-item">
                                <span class="wl-m-label">Margin</span>
                                <span class="wl-m-value" style="color: ${mosColor}">${data.is_loading ? loadingSpinner : mosStr}</span>
                            </div>
                        </div>
                        <div class="wl-scores-row">
                            <div class="wl-score-pill">
                                <div class="wl-dot ${hDotClass}"></div>
                                <span>Health: ${displayHealth || 'N/A'}</span>
                            </div>
                            <div class="wl-score-pill">
                                <div class="wl-dot ${dotClass}"></div>
                                <span>Buy: ${displayBuy || 'N/A'}</span>
                            </div>
                            <div class="wl-score-pill" title="Piotroski F-Score">
                                <span style="font-size: 0.75rem; font-weight: 800; margin-right: 4px; color: ${data.piotroski_score >= 7 ? 'var(--accent)' : (data.piotroski_score >= 4 ? '#fbbf24' : (data.piotroski_score == null ? 'var(--text-muted)' : 'var(--danger)'))}">
                                    ${data.piotroski_score != null ? data.piotroski_score : '--'}
                                </span>
                                <span style="font-size: 0.7rem; color: var(--text-muted);">Piotroski</span>
                            </div>
                        </div>
                    `;
                    
                    card.addEventListener('click', (e) => {
                        if (e.target.closest('.wl-close-btn')) return;
                        
                        // v39: Immediate UI feedback
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                        tickerInput.value = data.ticker;
                        analyzeTicker(data.ticker);
                    });

                    card.querySelector('.wl-close-btn').addEventListener('click', (e) => {
                        e.stopPropagation();
                        watchlist = watchlist.filter(t => t !== data.ticker);
                        cachedWatchlistData = cachedWatchlistData.filter(d => d.ticker !== data.ticker);
                        deleteOverrideFromServer(data.ticker);
                        saveWatchlist();
                        renderWatchlistUI();
                        if (currentTicker === data.ticker) updateWatchlistButtonState();
                    });
                    
                    watchlistGrid.appendChild(card);
                } catch (cardErr) {
                    console.error(`Error rendering card for ${data.ticker}:`, cardErr);
                }
            });
        } catch (err) {
            console.error("CRITICAL ERROR in renderWatchlistUI:", err);
            if (watchlistGrid) watchlistGrid.innerHTML = `<div style="color:red; padding:20px;">Error rendering watchlist: ${err.message}. Check console.</div>`;
        }
    };

    // ── Autocomplete Logic ──────────────────────────────
    let autocompleteTimeout = null;
    let selectedIndex = -1;

    const renderAutocomplete = (suggestions) => {
        autocompleteList.innerHTML = '';
        if (!suggestions || suggestions.length === 0) {
            autocompleteList.style.display = 'none';
            return;
        }

        suggestions.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = 'autocomplete-item';
            div.innerHTML = `
                <span class="ticker-match">${item.ticker}</span>
                <span class="name-match">${item.name}</span>
                <span class="exch-match">${item.exchange}</span>
            `;
            div.addEventListener('click', () => {
                tickerInput.value = item.ticker;
                analyzeTicker(item.ticker);
                autocompleteList.style.display = 'none';
            });
            autocompleteList.appendChild(div);
        });
        autocompleteList.style.display = 'block';
        selectedIndex = -1;
    };

    const handleAutocomplete = async () => {
        const query = tickerInput.value.trim();
        if (query.length < 1) {
            autocompleteList.style.display = 'none';
            return;
        }

        try {
            const res = await fetch(`/api/search/${encodeURIComponent(query)}?t=${Date.now()}`);
            if (res.ok) {
                const suggestions = await res.json();
                renderAutocomplete(suggestions);
            }
        } catch (err) {
            console.error('Autocomplete error:', err);
        }
    };

    tickerInput.addEventListener('input', () => {
        clearTimeout(autocompleteTimeout);
        autocompleteTimeout = setTimeout(handleAutocomplete, 300);
    });

    tickerInput.addEventListener('keydown', (e) => {
        const items = autocompleteList.querySelectorAll('.autocomplete-item');
        if (autocompleteList.style.display === 'block' && items.length > 0) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = (selectedIndex + 1) % items.length;
                updateSelection(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = (selectedIndex - 1 + items.length) % items.length;
                updateSelection(items);
            } else if (e.key === 'Enter' && selectedIndex >= 0) {
                e.preventDefault();
                const ticker = items[selectedIndex].querySelector('.ticker-match').textContent;
                tickerInput.value = ticker;
                analyzeTicker(ticker);
                autocompleteList.style.display = 'none';
            } else if (e.key === 'Escape') {
                autocompleteList.style.display = 'none';
            }
        }
    });

    const updateSelection = (items) => {
        items.forEach((item, idx) => {
            if (idx === selectedIndex) item.classList.add('selected');
            else item.classList.remove('selected');
        });
    };

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.autocomplete-wrapper')) {
            autocompleteList.style.display = 'none';
        }
    });

    // Event Listeners
    searchBtn.addEventListener('click', analyzeTicker);
    tickerInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') analyzeTicker(); });
    
    logoBtn.addEventListener('click', () => {
        if(currentTicker) {
            watchlistView.style.display = 'none';
            dashboard.style.display = 'block';
        }
    });

    const refreshWatchlistData = async () => {
        if (!watchlist || watchlist.length === 0) return;
        
        if (!window._watchlistFetching) window._watchlistFetching = new Set();
        if (!cachedWatchlistData) cachedWatchlistData = [];

        // Progressive Fetch: Call each ticker individually in parallel
        watchlist.forEach(async (ticker) => {
            const tUpper = ticker.toUpperCase();
            if (window._watchlistFetching.has(tUpper)) return; // Already fetching
            
            window._watchlistFetching.add(tUpper);
            if (watchlistView.style.display === 'block') renderWatchlistUI();

            try {
                // v38: Call individual valuation endpoint. 
                // skip_peers=false to ensure scores are 100% sync'd with dashboard.
                // Check client-side cache first (15 min TTL)
                const cacheKey = `valuation_${tUpper}`;
                const cached = sessionStorage.getItem(cacheKey);
                if (cached) {
                    const { data: cachedData, ts } = JSON.parse(cached);
                    if (Date.now() - ts < 15 * 60 * 1000) {
                        // Use cached data
                        const idx = cachedWatchlistData.findIndex(d => d.ticker.toUpperCase() === tUpper);
                        if (idx !== -1) cachedWatchlistData[idx] = cachedData; else cachedWatchlistData.push(cachedData);
                        return; // skip network fetch
                    }
                }
                const res = await fetch(`/api/valuation/${tUpper}?t=${Date.now()}`);
                if (res.ok) {
                    const data = await res.json();
                    // Store in sessionStorage
                    sessionStorage.setItem(cacheKey, JSON.stringify({ data, ts: Date.now() }));
                    const idx = cachedWatchlistData.findIndex(d => d.ticker.toUpperCase() === tUpper);
                    if (idx !== -1) {
                        cachedWatchlistData[idx] = data;
                    } else {
                        cachedWatchlistData.push(data);
                    }
                }
            } catch (e) {
                console.error(`Individual fetch failed for ${tUpper}`, e);
            } finally {
                window._watchlistFetching.delete(tUpper);
                if (watchlistView.style.display === 'block') renderWatchlistUI();
            }
        });
    };

    navWatchlistBtn.addEventListener('click', async () => {
        dashboard.style.display = 'none';
        watchlistView.style.display = 'block';
        
        if (!cachedWatchlistData || cachedWatchlistData.length !== watchlist.length) {
            loadingState.style.display = 'flex';
            watchlistView.style.display = 'none';
            await refreshWatchlistData();
            loadingState.style.display = 'none';
            watchlistView.style.display = 'block';
        }
        
        renderWatchlistUI();
    });

    addToWatchlistBtn.addEventListener('click', toggleWatchlist);

    // Watchlist Sort Dropdown
    const wlSortSelect = document.getElementById('wl-sort-select');
    if (wlSortSelect) {
        wlSortSelect.addEventListener('change', (e) => {
            const val = e.target.value; // e.g. "mos-desc"
            const [col, ord] = val.split('-');
            currentSort = { column: col, order: ord };
            manualOrder = false;
            renderWatchlistUI();
        });
    }

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

                const method = document.getElementById('dcf-method-selector')?.value || 'perpetual';
                const renderDCFView = (yp) => {
                    const dataObj = method === 'multiple' ? d.dcf_exit_multiple : d.dcf_perpetual;
                    if (!dataObj) return '<p style="color:var(--text-muted);">Data not available for this method.</p>';
                    
                    const fcfYears = dataObj.fcf_projections || [];
                    const sensMatrix = method === 'perpetual' ? (dataObj.sensitivity_matrix || []) : [];
                    
                    let tableHTML = `<table style="width:100%; border-collapse:collapse; margin-top:20px; font-size: 0.95rem;">
                                        <tr style="border-bottom:1px solid rgba(255,255,255,0.2);"><th style="text-align:left; padding:8px 0; color:white;">Year</th><th style="text-align:right; padding:8px 0; color:white;">Projected FCF</th></tr>`;
                    fcfYears.forEach((val, i) => {
                        tableHTML += `<tr><td style="padding:6px 0; color:white;">Year ${i+1}</td><td style="text-align:right; color:white;">${fmtBig(val)}</td></tr>`;
                    });
                    tableHTML += `</table>`;

                    const tvLabel = method === 'perpetual' ? `Terminal Value (${fmtPct(dataObj.perpetual_growth_rate)} Growth)` : `Terminal Value (${dataObj.exit_multiple}x Multiple)`;

                    let matrixHTML = '';
                    if (method === 'perpetual' && sensMatrix.length > 0) {
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
                        <div style="background:rgba(255,255,255,0.02); padding:20px; border-radius:8px; border:1px solid rgba(255,255,255,0.05); margin-bottom:20px;">
                            <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:var(--text-muted);">Discount Rate (Applied):</span><span style="font-weight:500; color:white;">${fmtPct(dataObj.discount_rate)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:var(--text-muted);">Growth Rate (Applied):</span><span style="font-weight:500; color:${d.eps_growth_applied < 0 ? 'var(--danger)' : 'white'};">${fmtPct(d.eps_growth_applied)}</span></div>
                            ${method === 'perpetual' ? `<div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:var(--text-muted);">Perpetual Growth:</span><span style="font-weight:500; color:white;">${fmtPct(dataObj.perpetual_growth_rate)}</span></div>` : `<div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:var(--text-muted);">Exit Multiple:</span><span style="font-weight:500; color:white;">${dataObj.exit_multiple}x</span></div>`}
                            <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:var(--text-muted);">Shares Outstanding:</span><span style="font-weight:500; color:white;">${d.shares_outstanding ? fmtBigNum(d.shares_outstanding, '') : 'N/A'}</span></div>
                        </div>

                        ${tableHTML}

                        <div style="margin-top:25px; border-top:1px solid rgba(255,255,255,0.1); padding-top:20px;">
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">Total PV of FCFs:</span><span style="font-weight:500; color:white;">${fmtBig(dataObj.present_value_fcf_sum)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">${tvLabel}:</span><span style="font-weight:500; color:white;">${fmtBig(dataObj.terminal_value)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">PV of Terminal Value:</span><span style="font-weight:500; color:white;">${fmtBig(dataObj.present_value_terminal)}</span></div>
                        </div>

                        <div style="margin-top:25px; border-top:1px solid rgba(255,255,255,0.1); padding-top:20px;">
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">+ Cash & Equivalents:</span><span style="font-weight:600; color:var(--accent);">${fmtBig(d.total_cash)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:5px 0;"><span style="color:var(--text-muted);">- Total Debt:</span><span style="font-weight:600; color:var(--danger);">${fmtBig(d.total_debt)}</span></div>
                        </div>

                        <div style="margin-top:20px; border-top:1px solid rgba(255,255,255,0.1); padding-top:20px;">
                            <div style="display:flex; justify-content:space-between; padding:10px 0; margin-top:5px;"><span style="color:var(--text-muted);">Intrinsic Value per Share:</span><span style="font-weight:800; color:var(--accent); font-size:1.15rem;">$${fmt(dataObj.fair_value_per_share)}</span></div>
                        </div>

                        ${matrixHTML}
                    `;
                };

                html = renderDCFView();
                body.innerHTML = html;
                modal.style.display = 'flex';
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
                     + row('Margin of Safety', (() => { const cp = globalData.current_price; const fv = g.fair_value; if (fv != null && cp > 0) { const mos = (fv - cp) / cp; return fmtPct(mos); } return 'N/A'; })());
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
            const label = (item.metric || item.name || 'Unknown Metric').split(' (')[0];
            const pts = (item.points_awarded !== undefined) ? item.points_awarded : (item.points || 0);
            const maxPts = item.max_points || 0;
            const pct = maxPts > 0 ? (pts / maxPts) : 0;

            // Dot color: green if >= 99% (full points), yellow if >= 40%, red otherwise
            let dotColor = 'var(--danger)';
            let ptsColor = 'var(--danger)';
            if (pct >= 0.99) { dotColor = 'var(--accent)'; ptsColor = 'var(--accent)'; }
            else if (pct >= 0.4) { dotColor = '#fbbf24'; ptsColor = '#fbbf24'; }

            html += `
                <div style="display:flex; align-items:center; justify-content:space-between; padding:14px 0; border-top:1px solid rgba(255,255,255,0.06);">
                    <div style="flex:1; min-width:0;">
                        <div style="font-weight:600; font-size:0.9rem; color:white;">${label}</div>
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
