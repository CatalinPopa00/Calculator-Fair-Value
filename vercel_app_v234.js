document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('search-btn');
    const tickerInput = document.getElementById('ticker-input');

    const parseLocaleFloat = (val) => {
        if (val === null || val === undefined || val === '') return NaN;
        const cleaned = val.toString().trim().replace(',', '.');
        return parseFloat(cleaned);
    };

    const formatCleanInputVal = (val) => {
        if (val === null || val === undefined || val === '') return '';
        const num = parseLocaleFloat(val);
        if (isNaN(num)) return '';
        return num % 1 === 0 ? num.toString() : num.toFixed(1);
    };

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
    // ── Global Error Handling ─────────────────────────────────────────
    window.onerror = function(message, source, lineno, colno, error) {
        console.error('GLOBAL ERROR:', message, 'at', source, ':', lineno, ':', colno);
        return false; // Let browser handle it too
    };
    window.onunhandledrejection = function(event) {
        console.error('UNHANDLED PROMISE REJECTION:', event.reason);
    };

    let currentTicker = null;
    let currentHealthBreakdown = null;
    let currentBuyBreakdown = null;
    let currentPiotroskiBreakdown = null;
    let chartRevFcf = null;
    let chartEpsShares = null;
    let globalData = null; 
    let _realApiPrice = null; // v299: Immutable anchor for Fair Value stability
    let _originalPrice = null; // Stores the restore point for simulation reset
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

    const getTargetPe = (sector, industry) => {
        const s_low = (sector || "").toLowerCase();
        const i_low = (industry || "").toLowerCase();
        if (s_low.includes('technology') || i_low.includes('software') || s_low.includes('communication')) return 25.0;
        if (s_low.includes('consumer discretionary')) return 22.0;
        if (s_low.includes('health') || i_low.includes('biotech')) return 18.0;
        if (['industrials', 'materials', 'consumer staples', 'defensive'].some(x => s_low.includes(x))) return 16.0;
        if (['utilities', 'real estate', 'reit'].some(x => s_low.includes(x))) return 15.0;
        if (s_low.includes('financial') || i_low.includes('bank')) return 13.0;
        return 18.0;
    };

    const recalcWithSimPrice = (simPrice) => {
        if (!globalData || !globalData.company_profile) return;

        // Helper to convert growth/margins to percentage if they are raw decimals (matches backend clean_percent)
        const cleanPercent = (val) => {
            if (val === null || val === undefined) return 0;
            let fVal = parseFloat(val);
            if (isNaN(fVal)) return 0;
            // Standardize decimal (0.05 -> 5%) before calculation
            if (Math.abs(fVal) > 0 && Math.abs(fVal) < 10.0) {
                return fVal * 100.0;
            }
            return fVal;
        };

        const prof = globalData.company_profile;
        const fairValue = globalData.fair_value;
        // v60: Use derived anchors for stability (prevents drift between GAAP/Non-GAAP)
        const eps = (window._simAnchors && window._simAnchors.eps > 0) ? window._simAnchors.eps : (prof.trailing_eps || 0);
        const growthFromAnchor = (window._simAnchors && window._simAnchors.growth > 0) ? window._simAnchors.growth : (prof.revenue_growth || 10);
        
        const shares = prof.shares_outstanding || 0;
        // v279: Financials are at the root of globalData, not inside company_profile
        const revenue = globalData.revenue || 0;
        const ebitda = globalData.ebitda || 0;
        const pToB = globalData.price_to_book || 0;
        const bookValuePerShare = (pToB > 0) ? (_realApiPrice / pToB) : 0;
        const dividendRate = globalData.dividend_rate || 0;
        const pe5y = prof.historic_pe || 0;

        // --- 1. Recalculated Scalars ---
        const newMos = fairValue ? ((fairValue - simPrice) / simPrice) * 100 : null;
        
        // v73: Distinct P/E calculations for GAAP and Non-GAAP transparency
        const newTrailingPE = (prof.trailing_eps > 0) ? simPrice / prof.trailing_eps : 0;
        const newNonGaapPE  = (prof.adjusted_eps > 0) ? simPrice / prof.adjusted_eps : 0;
        const scoringPE     = (eps > 0) ? simPrice / eps : 0; // Use anchored EPS for scoring (v72 logic)

        const newPS = (revenue > 0 && shares > 0) ? simPrice / (revenue / shares) : 0;
        const newMktCap = simPrice * shares;
        const ev = newMktCap + (globalData.total_debt || 0) - (globalData.total_cash || 0);
        const newEvEbitda = (ebitda > 0) ? ev / ebitda : 0;
        const newPB = (bookValuePerShare > 0) ? simPrice / bookValuePerShare : 0;
        const newDivYield = (simPrice > 0 && dividendRate > 0) ? (dividendRate / simPrice) : 0;

        // --- 2. Update Profile Metrics ---
        const updateMetric = (idSuffix, newValStr) => {
            const el = document.getElementById(`metric-val-${idSuffix}`);
            if (el) {
                el.textContent = newValStr;
                el.style.color = _simulating ? '#fbbf24' : 'white';
            }
        };

        // Price-dependent metrics
        updateMetric('marketcap', formatBigNumber(newMktCap, '$'));
        updateMetric('petrailing', newTrailingPE > 0 ? newTrailingPE.toFixed(2) + 'x' : 'N/A');
        updateMetric('penongaap', newNonGaapPE > 0 ? newNonGaapPE.toFixed(2) + 'x' : 'N/A');
        
        const newPeFwd = prof.fwd_eps > 0 ? simPrice / prof.fwd_eps : 0;
        updateMetric('pefwd', newPeFwd > 0 ? newPeFwd.toFixed(2) + 'x' : 'N/A');
        updateMetric('5yavgpe', prof.historic_pe ? prof.historic_pe.toFixed(2) + 'x' : 'N/A');
        
        let pegUsedGrowth = prof.earnings_growth || 0;
        const pegSrcEl = document.getElementById('peg-eps-source');
        if (pegSrcEl && pegSrcEl.value === 'custom') {
            const rawG = document.getElementById('peg-custom-growth').value;
            if (rawG !== '' && !isNaN(parseFloat(rawG))) {
                pegUsedGrowth = parseFloat(rawG) / 100;
            }
        } else if (globalData.formula_data && globalData.formula_data.peg) {
            pegUsedGrowth = globalData.formula_data.peg.eps_growth_estimated || pegUsedGrowth;
        }
        
        const newPeg = (pegUsedGrowth > 0 && newNonGaapPE > 0) ? newNonGaapPE / (pegUsedGrowth * 100) : 0;
        updateMetric('peg', newPeg > 0 ? newPeg.toFixed(2) : 'N/A');
        
        updateMetric('ps', newPS > 0 ? newPS.toFixed(2) + 'x' : 'N/A');
        
        const fwd_rev_per_share = prof.fwd_ps > 0 ? (_realApiPrice / prof.fwd_ps) : 0;
        const newPsFwd = fwd_rev_per_share > 0 ? simPrice / fwd_rev_per_share : 0;
        updateMetric('psfwd', newPsFwd > 0 ? newPsFwd.toFixed(2) + 'x' : 'N/A');
        
        const fcfPerShare = prof.pfcf_ratio > 0 ? (_realApiPrice / prof.pfcf_ratio) : 0;
        const newPfcf = fcfPerShare > 0 ? simPrice / fcfPerShare : 0;
        updateMetric('pfcf', newPfcf > 0 ? newPfcf.toFixed(2) + 'x' : 'N/A');
        
        updateMetric('dividendyield', formatSafePct(newDivYield));

        // --- 3. Update Current Price Header ---
        const priceEl = document.getElementById('current-price');
        if (priceEl && !_simulating) {
            priceEl.textContent = formatCurrency(simPrice);
        }

        // Precise growth rate calculation for simulation scoring to prevent drift
        const growthForScoring = pegUsedGrowth > 0 ? pegUsedGrowth * 100.0 : cleanPercent(prof.revenue_growth || 10);

        // --- 4. Predictive Scoring Logic (v70: Matches backend scoring.py thresholds) ---
        if (currentBuyBreakdown) {
            currentBuyBreakdown.forEach(item => {
                const metric = item.metric || '';
                let newPts = item.points_awarded;

                // Sector detection (matches scoring.py logic)
                const industry = (prof.industry || '').toLowerCase();
                const sector = (prof.sector || '').toLowerCase();
                const isFin = sector.includes('financial');
                const isBank = (industry.includes('bank') || industry.includes('credit services') || industry.includes('savings'));
                const isREIT = sector.includes('real estate') || sector.includes('reit');

                if (metric === 'Margin of Safety') {
                    if (isFin && isBank) {
                        newPts = (newMos > 20) ? 25 : (newMos >= 0 ? 12.5 : 0);
                    } else {
                        newPts = (newMos > 20) ? 30 : (newMos >= 0 ? 15 : 0);
                    }
                    item.value = formatPercent(newMos);
                } else if (metric.includes('P/E Ratio')) {
                    const target_pe = getTargetPe(sector, industry);
                    let pts = 0;
                    if (scoringPE > 0) {
                        if (scoringPE <= target_pe) {
                            pts = 20;
                        } else if (scoringPE <= target_pe * 1.3) {
                            const rev_g_val = cleanPercent(prof.revenue_growth || 0);
                            const peg_val = (growthForScoring > 0) ? scoringPE / growthForScoring : 0;
                            if (rev_g_val > 15 || (peg_val > 0 && peg_val < 1.5)) {
                                pts = 15;
                            } else {
                                pts = 10;
                            }
                        }
                    }
                    newPts = pts;
                    
                    // v72: Dynamic label based on simulation anchor (adj for Tech/Health)
                    const isTech = (sector.includes('technology') || sector.includes('communication') || industry.includes('software') || industry.includes('internet'));
                    const isHealth = sector.includes('healthcare');
                    item.metric = (isTech || isHealth) ? "P/E Ratio (adj.)" : "P/E Ratio (Trailing)";
                    item.value = scoringPE > 0 ? scoringPE.toFixed(2) + 'x' : '0.00x';
                } else if (metric === 'P/S Ratio') {
                    const target_pe = getTargetPe(sector, industry);
                    const margin = cleanPercent(globalData.company_profile.ebit_margin || globalData.company_profile.operating_margin || 0); 
                    const target_ps = target_pe * (margin / 100.0);
                    let pts = 0;
                    if (newPS > 0) {
                        if (margin < 0) {
                            const rev_g_val = cleanPercent(prof.revenue_growth || 0);
                            if (rev_g_val > 20 && newPS <= 5.0) pts = 5;
                        } else {
                            if (newPS <= target_ps) pts = 10;
                            else if (newPS <= target_ps * 1.5) pts = 5;
                        }
                    }
                    newPts = pts;
                    item.value = newPS > 0 ? newPS.toFixed(2) + 'x' : '0.00x';
                } else if (metric === 'EV / EBITDA') {
                    newPts = (newEvEbitda > 0 && newEvEbitda < 12) ? 10 : ((newEvEbitda > 0 && newEvEbitda <= 18) ? 5 : 0);
                    item.value = newEvEbitda > 0 ? newEvEbitda.toFixed(2) + 'x' : '0.00x';
                } else if (metric === 'Price-to-Book' || metric === 'P/B Ratio') {
                    newPts = (newPB > 0 && newPB < 1.2) ? 15 : ((newPB > 0 && newPB <= 2.0) ? 7.5 : 0);
                    item.value = newPB > 0 ? newPB.toFixed(2) + 'x' : '0.00x';
                } else if (metric === 'Dividend Yield') {
                    const dyPct = newDivYield * 100;
                    if (isREIT) newPts = dyPct > 5 ? 15 : (dyPct >= 3 ? 7.5 : 0);
                    else if (isFin) newPts = dyPct > 4 ? 15 : (dyPct >= 2 ? 7.5 : 0);
                    else newPts = 0; // Default template doesn't use DY for scoring points usually
                    item.value = dyPct.toFixed(1) + '%';
                } else if (metric === 'PEG Ratio') {
                    const newPEG = (growthForScoring > 0) ? scoringPE / growthForScoring : 0;
                    if (isFin) newPts = (newPEG > 0 && newPEG < 1.0) ? 15 : ((newPEG > 0 && newPEG <= 1.5) ? 7.5 : 0);
                    else newPts = (newPEG > 0 && newPEG < 1.0) ? 10 : ((newPEG > 0 && newPEG <= 1.5) ? 5 : 0);
                    item.value = newPEG > 0 ? newPEG.toFixed(2) + 'x' : '0.00x';
                } else if (metric === 'FCF Yield') {
                    const fyPct = (fcfPerShare > 0) ? (fcfPerShare / simPrice) * 100 : 0;
                    newPts = fyPct > 10 ? 15 : (fyPct >= 5 ? 7.5 : 0);
                    item.value = fyPct.toFixed(1) + '%';
                } else if (metric === 'P/AFFO') {
                    const affoPerShare = prof.price_to_affo > 0 ? (_originalPrice / prof.price_to_affo) : 0;
                    const newPAFFO = affoPerShare > 0 ? simPrice / affoPerShare : 0;
                    let pts = 0;
                    if (newPAFFO > 0) {
                        if (newPAFFO <= 15) {
                            pts = 20;
                        } else if (newPAFFO <= 15 * 1.3) {
                            const affo_g_val = prof.affo_growth || 0;
                            if (affo_g_val > 15) pts = 15;
                            else pts = 10;
                        }
                    }
                    newPts = pts;
                    item.value = newPAFFO > 0 ? newPAFFO.toFixed(2) + 'x' : '0.00x';
                }

                item.points_awarded = Math.min(newPts, item.max_points);
            });
        }

        // --- 5. Global Visual Re-sync ---
        if (window.triggerRecalculate) {
            window.triggerRecalculate();
        }

        // --- 6. Refresh Score Dashboard ---
        const totalBuy = currentBuyBreakdown.reduce((sum, item) => sum + (item.points_awarded || 0), 0);
        globalData.good_to_buy_total = Math.min(Math.max(totalBuy, 0), 100);
        updateScoreUI(globalData.good_to_buy_total, 'buy-score-circle', 'buy-score-fill');

        // --- 7. Update Open Modal (Real-time Simulation) ---
        const scoreModal = document.getElementById('score-modal');
        if (scoreModal && scoreModal.style.display === 'flex') {
            const titleEl = document.getElementById('score-modal-title');
            if (titleEl && titleEl.textContent.includes('Good to Buy')) {
                renderScoreBreakdown('Good to Buy Score Breakdown', globalData.good_to_buy_total, currentBuyBreakdown);
            }
        }

        // --- 8. Quick Strengths/Risks Update ---
        const allMetrics = [...(currentHealthBreakdown || []), ...(currentBuyBreakdown || [])];
        const strengths = allMetrics.filter(m => m.points_awarded === m.max_points && m.max_points > 0).sort((a,b) => b.max_points - a.max_points);
        const risks = allMetrics.filter(m => m.points_awarded === 0 && m.max_points > 0).sort((a,b) => b.max_points - a.max_points);

        const sList = document.getElementById('top-strengths-list');
        if (sList) {
            sList.innerHTML = strengths.slice(0, 3).map(s => `<li>${s.metric.split(' (')[0]}: ${s.value}</li>`).join('');
        }
        const rList = document.getElementById('risk-factors-list');
        if (rList) {
            rList.innerHTML = risks.slice(0, 3).map(r => `<li>${r.metric.split(' (')[0]}: ${r.value}</li>`).join('');
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

    // UPDATED: Sync both MOS and PEG to the Score Breakdown dynamically (v70)
    const updateInsightsAndScores = (newMos, newPeg) => {
        if (!currentBuyBreakdown || !globalData) return;

        // Ensure Buy Breakdown reflects the latest MOS and PEG from the primary engine
        const mosItem = currentBuyBreakdown.find(i => i.metric && i.metric.includes("Margin of Safety"));
        if (mosItem && newMos != null) {
            mosItem.value = `${newMos.toFixed(1)}%`;
            mosItem.points_awarded = (newMos > 20.0) ? 30 : (newMos >= 0.0 ? 15 : 0);
        }

        const pegItem = currentBuyBreakdown.find(i => i.metric && i.metric.includes("PEG Ratio"));
        if (pegItem && newPeg != null) {
            pegItem.value = `${newPeg.toFixed(2)}x`;
            const industry = (globalData.company_profile?.industry || "").toLowerCase();
            const sector = (globalData.company_profile?.sector || "").toLowerCase();
            const isFin = sector.includes('financial');
            
            if (isFin) pegItem.points_awarded = (newPeg > 0 && newPeg < 1.0) ? 15 : (newPeg > 0 && newPeg <= 1.5 ? 7.5 : 0);
            else pegItem.points_awarded = (newPeg > 0 && newPeg < 1.0) ? 10 : (newPeg > 0 && newPeg <= 1.5 ? 5 : 0);
        }

        if (typeof globalData.good_to_buy_total === 'number') {
            const rawTotal = currentBuyBreakdown.reduce((sum, item) => sum + (item.points_awarded || 0), 0);
            globalData.good_to_buy_total = Math.min(Math.max(rawTotal, 0), 100);
            
            // Re-sync all score circles during this pass
            updateScoreUI(globalData.health_score_total, 'health-score-circle', 'health-score-fill');
            updateScoreUI(globalData.good_to_buy_total, 'buy-score-circle', 'buy-score-fill');
            updatePiotroskiUI(globalData.piotroski ? globalData.piotroski.score : null);
            updateRule40UI(globalData.rule_of_40);
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

    const calcLocalDcf = (fcfObj, growth, wacc, perp, shares, cash, debt, buybackRate = 0, years = 5, exitMult = 10.0, currentPrice = null) => {
        let fcf = 0;
        let revenue = 0;
        let customMargin = null;
        let marginGrowth = 0.002;
        
        if (fcfObj && typeof fcfObj === 'object') {
            fcf = fcfObj.fcf || 0;
            revenue = fcfObj.revenue || 0;
            customMargin = fcfObj.customMargin;
            if (fcfObj.marginGrowth !== undefined && fcfObj.marginGrowth !== null) {
                marginGrowth = fcfObj.marginGrowth;
            }
        } else {
            fcf = fcfObj || 0;
        }

        if (!fcf || !shares || shares <= 0) return null;
        
        // WACC Smart Cap
        const finalWacc = Math.max(0.07, Math.min(wacc, 0.105));
        
        // 1. Determine base Revenue and starting FCF Margin
        let currentRevenue = revenue;
        if (!currentRevenue || currentRevenue <= 0) {
            currentRevenue = fcf / 0.10; // Fallback if revenue is missing
        }
        
        let startingFcfMargin = 0.10;
        if (customMargin !== null && !isNaN(customMargin)) {
            startingFcfMargin = customMargin / 100;
        } else if (currentRevenue > 0) {
            startingFcfMargin = fcf / currentRevenue;
        }
        
        let pv = 0;
        let currentFcf = fcf;
        const fcf_projections = [];
        const pv_fcf_years = [];
        
        // Method A Buyback tracking
        let remainingShares = shares;
        const buybackCostPerYear = [];
        
        for (let i = 1; i <= years; i++) {
            // Support multi-phase growth: growth can be an array (per-year) or a single number
            const g = Array.isArray(growth) ? (growth[i - 1] !== undefined ? growth[i - 1] : growth[growth.length - 1]) : growth;
            
            // Revenue grows year-over-year
            currentRevenue *= (1 + g);
            
            // FCF margin increases by configured growth rate each year in the background
            const yearMargin = startingFcfMargin + (i * marginGrowth);
            
            // FCF is calculated on top of projected Revenue
            currentFcf = currentRevenue * yearMargin;
            
            // Method A: Deduct buyback cash cost from FCF
            let buybackCashSpent = 0;
            if (buybackRate > 0 && currentPrice && currentPrice > 0) {
                const projectedPrice = currentPrice * Math.pow(1 + finalWacc, i);
                const sharesBought = remainingShares * buybackRate;
                buybackCashSpent = sharesBought * projectedPrice;
                remainingShares -= sharesBought;
                currentFcf -= buybackCashSpent;
            } else if (buybackRate > 0) {
                // Fallback: just reduce shares without FCF deduction
                remainingShares *= (1 - buybackRate);
            }
            
            buybackCostPerYear.push(buybackCashSpent);
            fcf_projections.push(currentFcf);
            
            const pv_fcf = currentFcf / Math.pow(1 + finalWacc, i);
            pv_fcf_years.push(pv_fcf);
            pv += pv_fcf;
        }
        
        const method = document.getElementById('dcf-method-selector')?.value || 'perpetual';
        let tv = 0;
        if (method === 'perpetual') {
            tv = (currentFcf * (1 + perp)) / (finalWacc - perp);
        } else {
            tv = currentFcf * exitMult;
        }
        
        const pvTv = tv / Math.pow(1 + finalWacc, years);
        const ev = pv + pvTv;
        const eqVal = ev + (cash || 0) - (debt || 0);
        if (eqVal <= 0) return null;
        const effectiveShares = remainingShares > 0 ? remainingShares : shares;
        const fair_value = eqVal / effectiveShares;
        
        return {
            fair_value,
            fcf_projections,
            pv_fcf_years,
            present_value_fcf_sum: pv,
            terminal_value: tv,
            present_value_terminal: pvTv,
            discount_rate: finalWacc,
            perpetual_growth_rate: perp,
            exit_multiple: exitMult,
            shares_outstanding: shares,
            effective_shares: effectiveShares,
            total_cash: cash || 0,
            total_debt: debt || 0,
            buyback_cost_per_year: buybackCostPerYear
        };
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

    // Helper for large numbers (B/M/K)
    const formatLargeNumber = (val, prefix = '', suffix = '') => {
        if (val === null || val === undefined || isNaN(val)) return '--';
        const absVal = Math.abs(val);
        if (absVal >= 1e9) return prefix + (val / 1e9).toFixed(2) + 'B' + suffix;
        if (absVal >= 1e6) return prefix + (val / 1e6).toFixed(2) + 'M' + suffix;
        if (absVal >= 1e3) return prefix + (val / 1e3).toFixed(2) + 'K' + suffix;
        return prefix + val.toFixed(2) + suffix;
    };

    // Safe Percentage Formatter for Tables
    const formatSafePct = (val) => {
        if (val === null || val === undefined || val === '') return 'N/A';
        const num = parseFloat(val);
        if (isNaN(num)) return 'N/A';
        return (num * 100).toFixed(1) + '%';
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
            <style>
                @media (max-width: 600px) {
                    .comparison-modal-card { padding: 15px !important; max-height: 95vh !important; }
                    .comparison-actions { flex-direction: column !important; align-items: stretch !important; }
                    .comparison-actions > div { max-width: 100% !important; flex-wrap: wrap !important; }
                    .comparison-actions input { flex: 1 1 100% !important; }
                    .comparison-actions button { flex: 1 1 auto !important; }
                }
            </style>
            <div id="comparison-modal" class="modal-overlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:9999; justify-content:center; align-items:center; backdrop-filter: blur(8px);">
                <div class="glass-card comparison-modal-card" style="width:95%; max-width:1000px; padding:25px; position:relative; display:flex; flex-direction:column; gap:20px; border: 1px solid rgba(255,255,255,0.1); overflow-y: auto; overflow-x: hidden; max-height: 90vh; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
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
        
        // Helper: safe calculation of P/FCF for main company
        const mainFcf = globalData?.formula_data?.dcf?.fcf || prof.fcf;
        const mainPfcf = prof.market_cap && mainFcf > 0 ? (prof.market_cap / mainFcf) : null;

        const mainComp = {
            ticker: prof.ticker || currentTicker,
            name: prof.name || 'Current',
            market_cap: prof.market_cap,
            pe_ratio: prof.trailing_pe,
            peg_ratio: globalData?.formula_data?.peg?.current_peg,
            eps: prof.trailing_eps,
            ps_ratio: prof.ps_ratio,
            revenue: globalData.revenue || (prof.market_cap && prof.ps_ratio && prof.ps_ratio > 0 ? prof.market_cap / prof.ps_ratio : null),
            pfcf_ratio: mainPfcf,
            fcf: mainFcf || (prof.market_cap && mainPfcf && mainPfcf > 0 ? prof.market_cap / mainPfcf : null),
            fcf_growth: prof.historic_fcf_growth,
            margin: prof.operating_margin,
            rev_growth: prof.revenue_growth,
            eps_growth: prof.earnings_growth
        };
        
        const competitors = prof.competitor_metrics || [];
        const all = [mainComp, ...competitors];
        
        const fmtPE = (v) => v != null && v > 0 ? v.toFixed(2) + 'x' : 'N/A';
        const fmtEPS = (v) => v != null ? '$' + v.toFixed(2) : 'N/A';
        const fmtMargin = (v) => v != null ? (v * 100).toFixed(2) + '%' : 'N/A';
        const fmtPctRow = (v) => {
            if (v == null) return 'N/A';
            const val = (v * 100).toFixed(2) + '%';
            let color = 'inherit';
            if (v > 0) color = 'var(--accent)';
            else if (v < 0) color = 'var(--danger)';
            return `<span style="color:${color};">${val}</span>`;
        };

        let html = `
        <div class="comparison-actions" style="display: flex; gap: 15px; margin-bottom: 20px; align-items: center; justify-content: space-between; flex-wrap: wrap; background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
            <div style="display: flex; gap: 8px; align-items: center; flex-grow: 1; max-width: 450px;">
                <input id="add-peer-input" type="text" placeholder="Add Competitor (e.g. MSFT)" style="flex: 1 1 150px; padding: 8px 12px; border-radius: 6px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: white; text-transform: uppercase; font-size: 0.9rem;">
                <button id="add-peer-btn" class="peer-btn" style="margin: 0; padding: 8px 16px; flex-shrink: 0;">Add</button>
                <button id="reset-peers-btn" class="peer-btn" style="margin: 0; padding: 8px 16px; background: rgba(239, 68, 68, 0.1); color: var(--danger); border-color: rgba(239, 68, 68, 0.3); flex-shrink: 0;">Reset</button>
            </div>
            <span id="add-peer-error" style="color: var(--danger); font-size: 0.85rem; font-weight: 500; display: none;"></span>
        </div>
        <div style="overflow-x: auto; border-radius: 12px;">
        <table style="width:100%; border-collapse:collapse; min-width: 750px; text-align: right;">
            <thead style="border-bottom: 2px solid rgba(255,255,255,0.1);">
                <tr>
                    <th style="padding:12px; text-align:left; color:var(--text-muted); font-size:0.85rem; position: sticky; left: 0; background: #0f172a; z-index: 10; border-right: 1px solid rgba(255,255,255,0.1);">COMPETITOR</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 100px;">Market Cap</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 110px;">P/E (Trailing)</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 100px;">PEG Ratio</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 110px;">EPS (Trailing)</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 110px;">P/S (Trailing)</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 120px;">Revenue (TTM)</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 100px;">P/FCF</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 110px;">FCF (Trailing)</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 130px;">Operating Margin</th>
                </tr>
            </thead>
            <tbody>
                ${all.map((c, i) => {
                    const isMain = i === 0;
                    
                    // Derive revenue and FCF from ratios if not directly available
                    const mCap = c.market_cap || c.marketCap;
                    const derivedRevenue = c.revenue || (mCap && c.ps_ratio && c.ps_ratio > 0 ? mCap / c.ps_ratio : null);
                    const derivedFcf = c.fcf || (mCap && c.pfcf_ratio && c.pfcf_ratio > 0 ? mCap / c.pfcf_ratio : null);
                    
                    return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); background: ${isMain ? 'rgba(56, 189, 248, 0.05)' : 'transparent'};">
                        <td style="padding:12px; text-align:left; font-weight:bold; color:${isMain ? 'var(--accent)' : 'white'}; position: sticky; left: 0; background: ${isMain ? '#122238' : '#0f172a'}; z-index: 10; border-right: 1px solid rgba(255,255,255,0.1); box-shadow: 2px 0 5px rgba(0,0,0,0.2);">
                            <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                                <span>${c.ticker}</span>
                                ${!isMain ? `<span class="delete-peer-btn" data-ticker="${c.ticker}" style="cursor:pointer; color:var(--danger); font-size:1.15rem; font-weight:bold; padding: 2px 6px; transition: color 0.15s;" title="Remove Peer">&times;</span>` : ''}
                            </div>
                        </td>
                        <td style="padding:12px; font-weight:bold;">${formatBigNumber(mCap, '$')}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtPE(c.pe_ratio)}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtPE(c.peg_ratio)}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtEPS(c.eps || c.trailing_eps)}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtPE(c.ps_ratio)}</td>
                        <td style="padding:12px; font-weight:bold;">${formatBigNumber(derivedRevenue, '$')}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtPE(c.pfcf_ratio)}</td>
                        <td style="padding:12px; font-weight:bold;">${formatBigNumber(derivedFcf, '$')}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtMargin(c.margin || c.operating_margin)}</td>
                    </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
        </div>`;
        
        container.innerHTML = html;
        document.getElementById('comparison-modal').style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // Setup reactive event listeners
        const addBtn = document.getElementById('add-peer-btn');
        const addInput = document.getElementById('add-peer-input');
        const errSpan = document.getElementById('add-peer-error');
        const resetBtn = document.getElementById('reset-peers-btn');
        
        if (resetBtn) {
            resetBtn.onclick = () => {
                localStorage.removeItem('customPeers_' + (prof.ticker || currentTicker));
                if (prof.original_competitor_metrics) {
                    prof.competitor_metrics = JSON.parse(JSON.stringify(prof.original_competitor_metrics));
                    prof.competitors = prof.competitor_metrics.map(p => p.ticker);
                }
                renderComparisonModal(prof);
            };
        }

        if (addBtn && addInput) {
            addBtn.onclick = async () => {
                const rawVal = addInput.value.trim().toUpperCase();
                if (!rawVal) return;
                
                errSpan.style.display = 'none';
                addBtn.disabled = true;
                addBtn.textContent = 'Fetching...';
                
                try {
                    const res = await fetch(`/api/valuation/${encodeURIComponent(rawVal)}?t=${Date.now()}&skip_peers=true`);
                    if (!res.ok) throw new Error('Ticker not found or valuation missing');
                    const peerData = await res.json();
                    
                    const peerProf = peerData.company_profile;
                    if (!peerProf) throw new Error('Invalid peer metrics received');
                    peerProf.ticker = peerProf.ticker || peerData.ticker || rawVal;
                    
                    const exists = (prof.competitor_metrics || []).some(p => p.ticker.toUpperCase() === rawVal);
                    if (exists) throw new Error('Peer is already in comparison');
                    
                    const mainFcf = peerData.formula_data?.dcf?.fcf || peerProf.fcf;
                    const pfcf = peerProf.market_cap && mainFcf > 0 ? (peerProf.market_cap / mainFcf) : null;
                    
                    const newPeerObj = {
                        ticker: peerProf.ticker.toUpperCase(),
                        name: peerProf.name || 'Competitor',
                        market_cap: peerProf.market_cap,
                        pe_ratio: peerProf.trailing_pe,
                        peg_ratio: peerData.formula_data?.peg?.current_peg,
                        trailing_eps: peerProf.trailing_eps,
                        eps: peerProf.trailing_eps,
                        ps_ratio: peerProf.ps_ratio,
                        price_to_book: peerProf.price_to_book,
                        ev_to_ebitda: peerData.formula_data?.relative?.company_ev_ebitda || peerProf.ev_to_ebitda,
                        revenue: peerProf.revenue,
                        pfcf_ratio: pfcf,
                        fcf: mainFcf,
                        margin: peerProf.operating_margin,
                        operating_margin: peerProf.operating_margin
                    };
                    
                    if (!prof.competitor_metrics) prof.competitor_metrics = [];
                    prof.competitor_metrics.push(newPeerObj);
                    
                    if (!prof.competitors) prof.competitors = [];
                    if (!prof.competitors.includes(rawVal)) prof.competitors.push(rawVal);
                    
                    // Persist to local storage
                    localStorage.setItem('customPeers_' + (prof.ticker || currentTicker), JSON.stringify(prof.competitor_metrics));
                    
                    // Update calculations and UI
                    updateFairValue();
                    renderComparisonModal(prof);
                    
                    if (typeof window._renderProfile === 'function') {
                        window._renderProfile();
                    }
                } catch (e) {
                    errSpan.textContent = e.message;
                    errSpan.style.display = 'inline';
                } finally {
                    addBtn.disabled = false;
                    addBtn.textContent = '➕ Add Peer';
                }
            };
            
            addInput.onkeydown = (ev) => {
                if (ev.key === 'Enter') addBtn.click();
            };
        }
        
        document.querySelectorAll('.delete-peer-btn').forEach(btn => {
            btn.onclick = () => {
                const t = btn.getAttribute('data-ticker');
                if (!t) return;
                
                prof.competitor_metrics = prof.competitor_metrics.filter(p => p.ticker.toUpperCase() !== t.toUpperCase());
                if (prof.competitors) {
                    prof.competitors = prof.competitors.filter(tk => tk.toUpperCase() !== t.toUpperCase());
                }
                
                // Persist
                localStorage.setItem('customPeers_' + (prof.ticker || currentTicker), JSON.stringify(prof.competitor_metrics));
                
                // Update calculations and UI
                updateFairValue();
                renderComparisonModal(prof);
                
                if (typeof window._renderProfile === 'function') {
                    window._renderProfile();
                }
            };
        });
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




    // ── Rule of 40 UI ──────────────────────────────────────────────────────────
    const updateRule40UI = (rule40Data) => {
        const circle = document.getElementById('rule40-score-circle');
        const fill   = document.getElementById('rule40-score-fill');
        if (!circle || !fill) return;

        // Reset
        circle.className = 'score-circle';
        fill.className = 'score-bar-fill';
        circle.style.color = '';
        fill.style.backgroundColor = '';
        fill.style.width = '0%';
        circle.style.width = 'auto'; // ensure padding is respected
        circle.style.padding = '0 10px';
        circle.style.borderRadius = '12px';

        if (!rule40Data || rule40Data.total === null || isNaN(rule40Data.total)) {
            circle.textContent = 'N/A';
            circle.style.color = 'var(--text-muted)';
            fill.style.backgroundColor = 'var(--text-muted)';
            return;
        }

        const total = rule40Data.total;
        circle.textContent = total.toFixed(1) + '%';
        
        // Bar width (cap at 100% of the bar, which represents 40% target)
        // If it's over 40%, the bar is 100% full.
        const target = 40.0;
        let barPct = Math.min((Math.max(total, 0) / target) * 100, 100);
        setTimeout(() => { fill.style.width = `${barPct}%`; }, 50);

        if (rule40Data.passed) {
            circle.classList.add('score-green');
            fill.classList.add('bg-score-green');
        } else if (total > 30) {
            circle.classList.add('score-yellow');
            fill.classList.add('bg-score-yellow');
        } else {
            circle.classList.add('score-red');
            fill.classList.add('bg-score-red');
        }
    };

    const renderRule40Breakdown = (rule40Data) => {
        const modalEl = document.getElementById('score-modal');
        const bodyEl  = document.getElementById('score-modal-body-content');
        if (!modalEl || !bodyEl) return;

        if (!rule40Data || rule40Data.total === null) {
            bodyEl.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 2rem;">No Rule of 40 data available.</p>`;
            modalEl.style.display = 'flex';
            return;
        }

        const total = rule40Data.total;
        const labelColor = rule40Data.passed ? 'var(--accent)' : (total > 30 ? '#fbbf24' : 'var(--danger)');
        const labelText  = rule40Data.label || (rule40Data.passed ? 'Strong' : (total > 30 ? 'Moderate' : 'Weak'));

        let html = `
            <div style="text-align:center; margin-bottom: 1.5rem;">
                <h3 style="font-size: 1.2rem; margin: 0 0 0.5rem; color: white;">Rule of 40 Breakdown</h3>
                <div style="font-size: 2.8rem; font-weight: 800; color: ${labelColor}; line-height: 1;">${total.toFixed(1)}%<span style="font-size: 1.2rem; color: var(--text-muted); font-weight: 500;">/40%</span></div>
                <div style="font-size: 0.9rem; font-weight: 700; color: ${labelColor}; margin-top: 4px;">${labelText}</div>
                <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 8px; max-width: 380px; margin-left: auto; margin-right: auto;">
                    Target: Revenue Growth + FCF Margin ≥ 40%
                </p>
            </div>
            
            <div style="margin-bottom: 1.2rem;">
                <h4 style="font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.6rem; border-bottom: 1px solid rgba(255,255,255,0.07); padding-bottom: 6px;">
                    Metrics
                </h4>
                
                <div style="display:flex; align-items:flex-start; gap:10px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
                    <span style="font-size:1.1rem; min-width:22px;">📈</span>
                    <div style="flex:1; min-width:0;">
                        <div style="font-size:0.85rem; font-weight:700; color:white;">Revenue Growth</div>
                        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">Most recent historical 1-year revenue growth.</div>
                    </div>
                    <span style="font-size:0.85rem; font-weight:700; color:var(--text-main); min-width:28px; text-align:right;">
                        ${(rule40Data.revenue_growth || 0).toFixed(1)}%
                    </span>
                </div>
                
                <div style="display:flex; align-items:flex-start; gap:10px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
                    <span style="font-size:1.1rem; min-width:22px;">💰</span>
                    <div style="flex:1; min-width:0;">
                        <div style="font-size:0.85rem; font-weight:700; color:white;">FCF Margin</div>
                        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">Free Cash Flow relative to Total Revenue.</div>
                    </div>
                    <span style="font-size:0.85rem; font-weight:700; color:var(--text-main); min-width:28px; text-align:right;">
                        ${(rule40Data.fcf_margin || 0).toFixed(1)}%
                    </span>
                </div>
            </div>`;

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
        let dcfValObj = null;
        if (currentFormulaData.dcf) {
            const fcfSourceEl = document.getElementById('fcf-source');
            const fcfSource = fcfSourceEl ? fcfSourceEl.value : 'custom';
            const yearsSourceEl = document.getElementById('dcf-years-source');
            const yearsVal = yearsSourceEl ? yearsSourceEl.value : '5yr';
            const years = yearsVal === '10yr' ? 10 : 5;
            const dcfData = currentFormulaData.dcf[yearsVal] || currentFormulaData.dcf["5yr"];
            
                const dcfInputs = document.getElementById('dcf-custom-inputs');
                if (dcfInputs) dcfInputs.style.display = fcfSource === 'custom' ? 'flex' : 'none';

                // v273: Growth rows 7-8 and 9-10 are now always visible if FCF Basis is Custom

                const buybackEl = document.getElementById('dcf-buyback-source');
                const buybackSrc = buybackEl ? buybackEl.value : 'none';
                const buybackCustomInputs = document.getElementById('dcf-buyback-custom-inputs');
                if (buybackCustomInputs) buybackCustomInputs.style.display = buybackSrc === 'custom' ? 'flex' : 'none';

                let buybackRate = 0;
                if (buybackSrc === 'historical') {
                    buybackRate = currentFormulaData.dcf.historic_buyback_rate || 0;
                } else if (buybackSrc === 'custom') {
                    const rawVal = document.getElementById('dcf-custom-buyback').value;
                    buybackRate = (rawVal === '' || isNaN(parseLocaleFloat(rawVal))) ? 0 : parseLocaleFloat(rawVal) / 100;
                }

                const baseFcf = currentFormulaData.dcf.fcf;
                const baseRevenue = globalData.revenue || (prof.market_cap && prof.ps_ratio && prof.ps_ratio > 0 ? prof.market_cap / prof.ps_ratio : null) || 0;
                
                const customMarginEl = document.getElementById('dcf-custom-fcf-margin');
                const customMargin = (customMarginEl && customMarginEl.value !== '') ? parseLocaleFloat(customMarginEl.value) : null;
                
                const customMarginGrowthEl = document.getElementById('dcf-custom-margin-growth');
                const customMarginGrowth = (customMarginGrowthEl && customMarginGrowthEl.value !== '') ? parseLocaleFloat(customMarginGrowthEl.value) / 100 : 0.002;
                
                const fcfParam = { fcf: baseFcf, revenue: baseRevenue, customMargin: customMargin, marginGrowth: customMarginGrowth };
                
                const shares = prof.shares_outstanding;
                
                // Dynamic WACC and Perpetual Growth from backend
                const w = currentFormulaData.dcf.discount_rate || 0.09;
                const p = currentFormulaData.dcf.perpetual_growth || 0.02;

                if (fcfSource === 'revenue' || fcfSource === 'eps_growth') {
                    const waccInput = document.getElementById('dcf-custom-wacc');
                    const wAnalyst = (waccInput && waccInput.value) ? parseLocaleFloat(waccInput.value)/100 : w;
                    
                    const pRaw = document.getElementById('dcf-custom-perp')?.value;
                    const pCustom = (pRaw === '' || isNaN(parseLocaleFloat(pRaw))) ? p : parseLocaleFloat(pRaw) / 100;
                    
                    const em = parseLocaleFloat(document.getElementById('input-exit-multiple')?.value) || (globalData.dcf_assumptions?.recommended_exit_multiple || 15.0);
                    
                    let g;
                    if (fcfSource === 'revenue') {
                        const getRevG = () => {
                            const rList = globalData.rev_estimates || [];
                            const ests = rList.filter(e => e && e.status !== 'reported' && e.growth != null);
                            if (ests.length >= 2) {
                                const g1 = parseLocaleFloat(ests[0].growth);
                                const g2 = parseLocaleFloat(ests[1].growth);
                                if (!isNaN(g1) && !isNaN(g2)) return (g1 + g2) / 2.0;
                            } else if (ests.length === 1) {
                                const g1 = parseLocaleFloat(ests[0].growth);
                                if (!isNaN(g1)) return g1;
                            }
                            if (prof && prof.revenue_growth != null) return prof.revenue_growth;
                            return 0.08;
                        };
                        const g13 = Math.round(getRevG() * 1000) / 1000;
                        const g46 = g13 - 0.02;
                        const g78 = g46 - 0.02;
                        const g910 = g78 - 0.02;
                        g = [];
                        for (let y = 1; y <= 10; y++) {
                            if (y <= 3) g.push(g13);
                            else if (y <= 6) g.push(g46);
                            else if (y <= 8) g.push(g78);
                            else g.push(g910);
                        }
                    } else {
                        g = currentFormulaData.dcf.eps_growth_applied || 0.10;
                    }
                    
                    if (currentFormulaData.dcf) currentFormulaData.dcf.eps_growth_applied = g;
                    
                    dcfValObj = calcLocalDcf(fcfParam, g, wAnalyst, pCustom, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years, em, globalData.current_price);
                }
                else if (fcfSource === 'historical') {
                    const hg13 = Math.round((prof.historic_fcf_growth != null ? prof.historic_fcf_growth : 0.05) * 1000) / 1000;
                    const hg46 = hg13 - 0.02;
                    const hg78 = hg46 - 0.02;
                    const hg910 = hg78 - 0.02;
                    const hgArray = [];
                    for (let y = 1; y <= 10; y++) {
                        if (y <= 3) hgArray.push(hg13);
                        else if (y <= 6) hgArray.push(hg46);
                        else if (y <= 8) hgArray.push(hg78);
                        else hgArray.push(hg910);
                    }
                    if (currentFormulaData.dcf) currentFormulaData.dcf.eps_growth_applied = hgArray;
                    const em = parseLocaleFloat(document.getElementById('input-exit-multiple')?.value) || (globalData.dcf_assumptions?.recommended_exit_multiple || 10.0);
                    dcfValObj = calcLocalDcf(fcfParam, hgArray, w, p, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years, em, globalData.current_price);
                } else if (fcfSource === 'custom') {
                    const getVal = (id) => {
                        const el = document.getElementById(id);
                        if (!el || el.value === '') return null;
                        return parseLocaleFloat(el.value);
                    };

                    const v13 = getVal('dcf-growth-1-3');
                    const v46 = getVal('dcf-growth-4-6');
                    const v78 = getVal('dcf-growth-7-8');
                    const v910 = getVal('dcf-growth-9-10');

                    // Strict validation: 1-3Y and 4-6Y are ALWAYS required for custom
                    if (v13 === null || v46 === null) {
                        dcfValObj = null;
                    } else if (years === 10 && (v78 === null || v910 === null)) {
                        // If 10yr selected, 7-8Y and 9-10Y are ALSO required
                        dcfValObj = null;
                    } else {
                        const g13 = v13 / 100;
                        const g46 = v46 / 100;
                        const g78 = (v78 ?? 0) / 100;
                        const g910 = (v910 ?? 0) / 100;

                        // Build per-year growth array
                        const growthArr = [];
                        for (let y = 1; y <= years; y++) {
                            if (y <= 3) growthArr.push(g13);
                            else if (y <= 6) growthArr.push(g46);
                            else if (y <= 8) growthArr.push(g78);
                            else growthArr.push(g910);
                        }

                        if (currentFormulaData.dcf) currentFormulaData.dcf.eps_growth_applied = growthArr;

                        const wRaw = document.getElementById('dcf-custom-wacc').value;
                        const pRaw = document.getElementById('dcf-custom-perp').value;
                        const emRaw = document.getElementById('input-exit-multiple').value;

                        const wCustom = (wRaw === '' || isNaN(parseLocaleFloat(wRaw))) ? 0.09 : parseLocaleFloat(wRaw) / 100;
                        const pCustom = (pRaw === '' || isNaN(parseLocaleFloat(pRaw))) ? 0.025 : parseLocaleFloat(pRaw) / 100;
                        const em = (emRaw === '' || isNaN(parseLocaleFloat(emRaw))) ? (globalData.dcf_assumptions?.recommended_exit_multiple || 10.0) : parseLocaleFloat(emRaw);

                        dcfValObj = calcLocalDcf(fcfParam, growthArr, wCustom, pCustom, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years, em, globalData.current_price);
                    }
                }

                if (dcfValObj) {
                    dcfVal = dcfValObj.fair_value;
                    
                    const method = document.getElementById('dcf-method-selector')?.value || 'perpetual';
                    const methodKey = method === 'multiple' ? 'dcf_exit_multiple' : 'dcf_perpetual';
                    
                    currentFormulaData.dcf[methodKey] = {
                        fair_value_per_share: dcfValObj.fair_value,
                        fcf_projections: dcfValObj.fcf_projections,
                        pv_fcf_years: dcfValObj.pv_fcf_years,
                        present_value_fcf_sum: dcfValObj.present_value_fcf_sum,
                        terminal_value: dcfValObj.terminal_value,
                        present_value_terminal: dcfValObj.present_value_terminal,
                        discount_rate: dcfValObj.discount_rate,
                        perpetual_growth_rate: dcfValObj.perpetual_growth_rate,
                        exit_multiple: dcfValObj.exit_multiple,
                        shares_outstanding: dcfValObj.shares_outstanding,
                        total_cash: dcfValObj.total_cash,
                        total_debt: dcfValObj.total_debt,
                        sensitivity_matrix: currentFormulaData.dcf[methodKey]?.sensitivity_matrix || []
                    };
                    
                    currentFormulaData.dcf.total_cash = dcfValObj.total_cash;
                    currentFormulaData.dcf.total_debt = dcfValObj.total_debt;
                    currentFormulaData.dcf.shares_outstanding = dcfValObj.shares_outstanding;
                } else {
                    dcfVal = null;
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
            if (pegInputs) pegInputs.style.display = pegSrc === 'custom' ? 'grid' : 'none';

            usedGrowth = currentFormulaData.peg.eps_growth_estimated || 0;
            if (pegSrc === '5ycagr') {
                usedGrowth = currentFormulaData.peg.eps_growth_5y_cagr || usedGrowth;
            } else if (pegSrc === 'custom') {
                const rawG = document.getElementById('peg-custom-growth').value;
                usedGrowth = (rawG === '' || isNaN(parseFloat(rawG))) ? 0.20 : parseFloat(rawG) / 100;
            }

            const eps = globalData.company_profile.adjusted_eps || globalData.company_profile.trailing_eps || 0;
            // v299: Use _realApiPrice for valuation anchor to prevent Fair Value drift during simulation
            const currentPe = (eps > 0) ? (_realApiPrice / eps) : (currentFormulaData.peg.current_pe || (parseFloat(globalData.company_profile.current_pe) || parseFloat(globalData.company_profile.trailing_pe) || 0));
            // v61: Default to 1.25 if industry_peg is missing (e.g. no peers found)
            const pegMode = document.getElementById('peg-mode')?.value || 'standard';
            const industryPegRaw = currentFormulaData.peg.industry_peg;
            
            const sector = globalData.company_profile.sector || "";
            const industry = globalData.company_profile.industry || "";
            const isTelecom = industry.toLowerCase().includes("telecom");
            
            let targetPeg = 1.0;
            if (pegMode === 'industry') {
                targetPeg = industryPegRaw || 1.25;
            } else {
                if (sector === "Technology" || (sector === "Communication Services" && !isTelecom)) {
                    targetPeg = 1.50;
                } else if (sector === "Utilities" || isTelecom) {
                    targetPeg = 1.00;
                } else if (sector === "Consumer Defensive") {
                    targetPeg = 1.50;
                } else if (sector === "Financial Services") {
                    targetPeg = 1.20;
                }
            }

            if (usedGrowth > 0 && currentPe > 0 && targetPeg > 0) {
                const originalPeg = currentPe / (usedGrowth * 100);
                pegVal = _realApiPrice * (targetPeg / originalPeg);
                
                // Calculate simulated PEG for display text only
                // v302: Scale by currentPrice/realApiPrice ratio for reactive simulation on all tickers
                const simPe = (eps > 0) ? (globalData.current_price / eps) : (currentPe * (globalData.current_price / _realApiPrice));
                currentPegToDisplay = simPe / (usedGrowth * 100);
                
                pegMos = ((pegVal - globalData.current_price) / globalData.current_price) * 100;
            } else if (pegSrc === 'analyst') {
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
            const pegMode = document.getElementById('peg-mode')?.value || 'standard';
            const industryPeg = currentFormulaData.peg ? currentFormulaData.peg.industry_peg : null;
            if (pegVal != null && currentPegToDisplay != null) {
                const sector = globalData.company_profile.sector || "";
                const industry = globalData.company_profile.industry || "";
                const isTelecom = industry.toLowerCase().includes("telecom");
                
                let targetPeg = 1.0;
                if (pegMode === 'industry') {
                    targetPeg = industryPeg || 1.25;
                } else {
                    if (sector === "Technology" || (sector === "Communication Services" && !isTelecom)) {
                        targetPeg = 1.50;
                    } else if (sector === "Utilities" || isTelecom) {
                        targetPeg = 1.00;
                    } else if (sector === "Consumer Defensive") {
                        targetPeg = 1.50;
                    } else if (sector === "Financial Services") {
                        targetPeg = 1.20;
                    }
                }

                const displayCurrent = currentPegToDisplay;
                const displayTarget = targetPeg;
                pegCompareElem.textContent = `PEG = ${displayCurrent.toFixed(2)} vs PEG ${pegMode === 'industry' ? 'Sector' : 'Std'} = ${displayTarget.toFixed(2)}`;
                
                // Store dynamics for modal
                currentFormulaData.peg.dynamic_growth = usedGrowth;
                currentFormulaData.peg.dynamic_fv = pegVal;
                currentFormulaData.peg.dynamic_peg = currentPegToDisplay;

                // ── SECTOR-SPECIFIC PEG THRESHOLDS (v291) ──
                const peg = currentPegToDisplay;
                
                let statusText = "";
                let statusColor = "var(--text-muted)";
                let subText = "";

                if (pegMode === 'industry' && industryPeg) {
                    if (peg < industryPeg * 0.8) { statusText = "UNDERVALUED (vs Sector)"; statusColor = "var(--accent)"; }
                    else if (peg <= industryPeg * 1.2) { statusText = "FAIR VALUE (vs Sector)"; statusColor = "#fbbf24"; }
                    else { statusText = "OVERVALUED (vs Sector)"; statusColor = "var(--danger)"; }
                    subText = `Sector Median PEG: ${industryPeg.toFixed(2)}`;
                } else if (sector === "Technology" || (sector === "Communication Services" && !isTelecom)) {
                    if (peg < 1.5) { statusText = "UNDERVALUED"; statusColor = "var(--accent)"; }
                    else if (peg <= 2.5) { statusText = "FAIR VALUE"; statusColor = "#fbbf24"; }
                    else { statusText = "OVERVALUED"; statusColor = "var(--danger)"; }
                } else if (sector === "Utilities" || isTelecom) {
                    if (peg < 1.0) { statusText = "UNDERVALUED / FAIR VALUE"; statusColor = "var(--accent)"; }
                    else { statusText = "OVERVALUED"; statusColor = "var(--danger)"; }
                    subText = "Note: PEGY is more accurate for this sector.";
                } else if (sector === "Consumer Defensive") {
                    if (peg < 1.5) { statusText = "UNDERVALUED"; statusColor = "var(--accent)"; }
                    else if (peg <= 2.0) { statusText = "FAIR VALUE"; statusColor = "#fbbf24"; }
                    else { statusText = "OVERVALUED"; statusColor = "var(--danger)"; }
                } else if (sector === "Financial Services") {
                    if (peg < 0.8) { statusText = "UNDERVALUED"; statusColor = "var(--accent)"; }
                    else if (peg <= 1.2) { statusText = "FAIR VALUE"; statusColor = "#fbbf24"; }
                    else { statusText = "OVERVALUED"; statusColor = "var(--danger)"; }
                } else if (["Industrials", "Energy", "Basic Materials"].includes(sector)) {
                    statusText = "CYCLICAL VERDICT";
                    statusColor = "#a855f7"; 
                    subText = "Compare directly with industry benchmarks (Cyclical Sector).";
                } else {
                    // Default Fallback (Standard PEG 1.0 logic)
                    if (peg < 1.0) { statusText = "UNDERVALUED"; statusColor = "var(--accent)"; }
                    else if (peg <= 1.5) { statusText = "FAIR VALUE"; statusColor = "#fbbf24"; }
                    else { statusText = "OVERVALUED"; statusColor = "var(--danger)"; }
                }

                pegStatusElem.textContent = statusText;
                pegStatusElem.style.color = statusColor;
            } else {
                pegStatusElem.textContent = "N/A";
                pegStatusElem.style.color = "var(--text-muted)";
                pegCompareElem.textContent = industryPeg == null ? "Sector data unavailable" : "PEG calculation data missing";
            }
        }

        const pegCardMos = document.getElementById('peg-card-mos');
        if (pegCardMos && pegVal != null) {
            const pegMos = ((pegVal - globalData.current_price) / globalData.current_price) * 100;
            pegCardMos.textContent = `MOS: ${formatPercent(pegMos)}`;
            pegCardMos.style.color = pegMos > 0 ? 'var(--accent)' : 'var(--danger)';
            pegCardMos.style.display = 'block';
        } else if (pegCardMos) {
            pegCardMos.style.display = 'none';
        }

        let lynchVal = null;
        if (currentFormulaData.peter_lynch) {
            const pl = currentFormulaData.peter_lynch;
            const epsSourceEl = document.getElementById('lynch-eps-source');
            const epsSource = epsSourceEl ? epsSourceEl.value : 'analyst';
            const lynchInputs = document.getElementById('lynch-custom-inputs');
            if (lynchInputs) lynchInputs.style.display = epsSource === 'custom' ? 'grid' : 'none';

            let usedGrowth = pl.eps_growth_estimated || 0.05;
            let baseEps = pl.valuation_eps || pl.trailing_eps || 0;
            let targetEps = baseEps * Math.pow(1 + usedGrowth, 3); // v288: Restored 3Y Compounded Projection

            if (epsSource === '5ycagr') {
                usedGrowth = pl.eps_growth_5y_cagr || usedGrowth;
                targetEps = baseEps * Math.pow(1 + usedGrowth, 3);
            } else if (epsSource === 'historical') {
                usedGrowth = prof.historic_eps_growth != null ? prof.historic_eps_growth : 0.05;
                targetEps = baseEps * Math.pow(1 + usedGrowth, 3);
            } else if (epsSource === 'custom') {
                const rawG = document.getElementById('lynch-custom-growth').value;
                usedGrowth = (rawG === '' || isNaN(parseFloat(rawG))) ? 0.20 : parseFloat(rawG) / 100;
                targetEps = baseEps * Math.pow(1 + usedGrowth, 3);
            }

            const multEl = document.getElementById('lynch-multiple-source');
            const multVal = multEl ? multEl.value : 'pe20';
            const multCustomInputs = document.getElementById('lynch-custom-multiple-inputs');
            if (multCustomInputs) multCustomInputs.style.display = multVal === 'custom' ? 'grid' : 'none';

            let selectedMult = 20; 
            if (multVal === 'pe15') selectedMult = 15;
            if (multVal === 'pe20') selectedMult = 20;
            if (multVal === 'pe25') selectedMult = 25;
            if (multVal === 'historical') selectedMult = pl.historic_pe || 20;
            if (multVal === 'custom') {
                selectedMult = parseFloat(document.getElementById('lynch-custom-mult').value) || 18;
            }

            if (targetEps != null && targetEps > 0) {
                // v46: Simple Future Project (no discounting per user preference)
                lynchVal = targetEps * selectedMult;
            }
            
            // Store dynamics for modal
            currentFormulaData.peter_lynch.dynamic_growth = usedGrowth;
            currentFormulaData.peter_lynch.dynamic_fwd_eps = targetEps;
            currentFormulaData.peter_lynch.dynamic_fv = lynchVal;
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
            const SECTOR_WEIGHTS = {
                'Technology': { PE: 0.35, EV_EBITDA: 0.50, PS: 0.15 },
                'Information Technology': { PE: 0.35, EV_EBITDA: 0.50, PS: 0.15 },
                'Technology_Growth': { PE: 0.00, EV_EBITDA: 0.20, PS: 0.80 },
                'Financial Services': { PE: 0.40, PB: 0.60 },
                'Financials': { PE: 0.40, PB: 0.60 },
                'Industrials': { PE: 0.20, EV_EBITDA: 0.80 },
                'Energy': { PE: 0.20, EV_EBITDA: 0.80 },
                'Consumer Defensive': { PE: 0.50, EV_EBITDA: 0.30, PS: 0.20 },
                'Consumer Staples': { PE: 0.50, EV_EBITDA: 0.30, PS: 0.20 },
                'Consumer Cyclical': { PE: 0.35, EV_EBITDA: 0.35, PS: 0.30 },
                'Consumer Discretionary': { PE: 0.35, EV_EBITDA: 0.35, PS: 0.30 },
                'Healthcare': { PE: 0.35, EV_EBITDA: 0.40, PS: 0.25 },
                'Health Care': { PE: 0.35, EV_EBITDA: 0.40, PS: 0.25 },
                'Communication Services': { PE: 0.35, EV_EBITDA: 0.40, PS: 0.25 },
                'Utilities': { PE: 0.50, EV_EBITDA: 0.50 },
                'Basic Materials': { PE: 0.25, EV_EBITDA: 0.75 },
                'Materials': { PE: 0.25, EV_EBITDA: 0.75 },
                'Real Estate': { PE: 0.00, P_FFO: 0.80, P_AFFO: 0.20 },
                'Default': { PE: 0.40, EV_EBITDA: 0.40, PS: 0.20 }
            };

            let fvPE = 0, fvPFCF = 0, fvPS = 0, fvPB = 0, fvEVEBITDA = 0;
            
            const company_eps = rel.company_eps || 0;
            const company_fcf_share = rel.company_fcf_share || 0;
            const company_sales_share = rel.company_sales_share || 0;
            const company_book_share = rel.company_book_share || 0;
            const company_ebitda = globalData.ebitda || 0;
            const company_debt = globalData.total_debt || 0;
            const company_cash = globalData.total_cash || 0;
            const company_shares = (globalData.company_profile && globalData.company_profile.shares_outstanding) || 1;

            const variantEl = document.getElementById('relative-variant');
            const variant = variantEl ? variantEl.value : 'peers';
            
            // Calculate dynamic peer medians and means
            const peers = (globalData && globalData.company_profile && globalData.company_profile.competitor_metrics) || [];
            
            const getMedian = (arr) => {
                const sorted = arr.filter(x => x != null && !isNaN(x)).sort((a, b) => a - b);
                if (sorted.length === 0) return null;
                const mid = Math.floor(sorted.length / 2);
                return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
            };

            const getMean = (arr) => {
                const valid = arr.filter(x => x != null && !isNaN(x));
                if (valid.length === 0) return null;
                return valid.reduce((sum, v) => sum + v, 0) / valid.length;
            };

            const dynamicMedians = {
                PE: getMedian(peers.map(p => p.pe_ratio)),
                PFCF: getMedian(peers.map(p => p.pfcf_ratio)),
                PS: getMedian(peers.map(p => p.ps_ratio)),
                PB: getMedian(peers.map(p => p.price_to_book)),
                EV_EBITDA: getMedian(peers.map(p => p.ev_to_ebitda))
            };

            const dynamicMeans = {
                PE: getMean(peers.map(p => p.pe_ratio)),
                PFCF: getMean(peers.map(p => p.pfcf_ratio)),
                PS: getMean(peers.map(p => p.ps_ratio)),
                PB: getMean(peers.map(p => p.price_to_book)),
                EV_EBITDA: getMean(peers.map(p => p.ev_to_ebitda))
            };

            let bPE = 20, bPFCF = 20, bPS = 2, bPB = 2, bEVEBITDA = 12;
            let multipleLabel = 'P/E';

            if (variant === 'peers') {
                bPE = dynamicMedians.PE ?? rel.median_peer_pe ?? 20;
                bPFCF = dynamicMedians.PFCF ?? rel.median_peer_pfcf ?? 20;
                bPS = dynamicMedians.PS ?? rel.median_peer_ps ?? 2;
                bPB = dynamicMedians.PB ?? rel.median_peer_pb ?? 2;
                bEVEBITDA = dynamicMedians.EV_EBITDA ?? rel.median_peer_ev_ebitda ?? 12;
                multipleLabel = `Peer Median P/E: ${bPE.toFixed(1)}x`;
            } else if (variant === 'average') {
                bPE = dynamicMeans.PE ?? rel.mean_peer_pe ?? 20;
                bPFCF = dynamicMeans.PFCF ?? rel.mean_peer_pfcf ?? 20;
                bPS = dynamicMeans.PS ?? rel.mean_peer_ps ?? 2;
                bPB = dynamicMeans.PB ?? rel.mean_peer_pb ?? 2;
                bEVEBITDA = dynamicMeans.EV_EBITDA ?? rel.mean_peer_ev_ebitda ?? 12;
                multipleLabel = `Peer Avg P/E: ${bPE.toFixed(1)}x`;
            } else { 
                bPE = rel.sp500_pe || 24.5;
                bPFCF = rel.sp500_pfcf || 28.0;
                bPS = rel.sp500_ps || 2.8;
                bPB = rel.sp500_pb || 4.5;
                bEVEBITDA = rel.sp500_ev_ebitda || 15.0;
                multipleLabel = `S&P 500 Trailing P/E: ${bPE.toFixed(1)}x`;
            }

            fvPE = company_eps * bPE;
            fvPFCF = company_fcf_share * bPFCF;
            fvPS = company_sales_share * bPS;
            fvPB = company_book_share * bPB;
            
            const impliedEV = company_ebitda * bEVEBITDA;
            const impliedMktCap = impliedEV - company_debt + company_cash;
            fvEVEBITDA = company_shares > 0 ? impliedMktCap / company_shares : 0;

            const sectorName = rel.sector || 'Default';
            let weights = SECTOR_WEIGHTS[sectorName] || SECTOR_WEIGHTS['Default'];
            
            // Technology Growth override: unprofitable or high-multiple tech
            if ((sectorName === 'Technology' || sectorName === 'Information Technology') &&
                (company_eps <= 0 || company_ebitda <= 0 || bPE > 50)) {
                weights = SECTOR_WEIGHTS['Technology_Growth'];
            }
            
            // Fuzzy fallback for rare/unmapped sector strings
            if (!SECTOR_WEIGHTS[sectorName]) {
                if (sectorName.includes('Tech')) weights = SECTOR_WEIGHTS['Technology'];
                else if (sectorName.includes('Finance') || sectorName.includes('Bank')) weights = SECTOR_WEIGHTS['Financial Services'];
                else if (sectorName.includes('Industrial')) weights = SECTOR_WEIGHTS['Industrials'];
                else if (sectorName.includes('Energy')) weights = SECTOR_WEIGHTS['Energy'];
                else if (sectorName.includes('Health')) weights = SECTOR_WEIGHTS['Healthcare'];
                else if (sectorName.includes('Real Estate') || sectorName.includes('REIT')) weights = SECTOR_WEIGHTS['Real Estate'];
                else if (sectorName.includes('Communication')) weights = SECTOR_WEIGHTS['Communication Services'];
                else if (sectorName.includes('Utilit')) weights = SECTOR_WEIGHTS['Utilities'];
                else if (sectorName.includes('Material')) weights = SECTOR_WEIGHTS['Materials'];
            }
            // Check if user has custom weights stored for this sector
            const customWKey = 'rel-weight-mode-card';
            const modeCardEl = document.getElementById(customWKey);
            if (modeCardEl && modeCardEl.value === 'custom' && window._relCustomWeights) {
                // Override weights with user's custom values
                const cw = window._relCustomWeights;
                Object.keys(cw).forEach(k => { if (weights[k] !== undefined) weights[k] = cw[k]; });
            }

            let weightedSum = 0;
            let totalWeight = 0;

            const calcMetric = (val, weight) => {
                if (weight != null && weight > 0) {
                    const safeVal = (val != null && isFinite(val) && val > 0) ? val : 0;
                    if (safeVal > 0) {
                        weightedSum += (safeVal * weight);
                        totalWeight += weight;
                    }
                }
            };

            if (weights.PE !== undefined) calcMetric(fvPE, weights.PE);
            if (weights.PFCF !== undefined) calcMetric(fvPFCF, weights.PFCF);
            if (weights.PS !== undefined) calcMetric(fvPS, weights.PS);
            if (weights.PB !== undefined) calcMetric(fvPB, weights.PB);
            if (weights.EV_EBITDA !== undefined) calcMetric(fvEVEBITDA, weights.EV_EBITDA);
            if (weights.P_FFO !== undefined) calcMetric(fvPE, weights.P_FFO);
            if (weights.P_AFFO !== undefined) calcMetric(fvPFCF, weights.P_AFFO);

            if (totalWeight > 0) {
                relVal = weightedSum / totalWeight;
            } else {
                relVal = fvPE > 0 ? fvPE : (fvPS > 0 ? fvPS : null);
            }

            const mc = document.getElementById('relative-market-compare');
            if (mc) mc.textContent = multipleLabel;
            
            // --- Populate custom weight inputs on the card ---
            const LABEL = { PE: 'P/E', PFCF: 'P/FCF', PS: 'P/S', PB: 'P/B', EV_EBITDA: 'EV/EBITDA', P_FFO: 'P/FFO', P_AFFO: 'P/AFFO' };
            const activeKeys = Object.keys(weights).filter(k => weights[k] !== undefined);
            const cwPanel = document.getElementById('rel-custom-weights-card');
            if (cwPanel) {
                const container = cwPanel.querySelector('div');
                if (container) {
                    container.innerHTML = activeKeys.map(k => `
                        <div style="display:flex; flex-direction:column; align-items:center; gap:2px;">
                            <label style="font-size:0.6rem; color:var(--text-muted); font-weight:600;">${LABEL[k] || k}</label>
                            <div style="display:flex; align-items:center; gap:1px;">
                                <input type="number" id="rel-cw-card-${k}" value="${((weights[k] || 0) * 100).toFixed(0)}" min="0" max="100" step="5"
                                    style="width:42px; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15); color:white; padding:3px 4px; border-radius:4px; font-size:0.7rem; text-align:center;">
                                <span style="font-size:0.6rem; color:var(--text-muted);">%</span>
                            </div>
                        </div>
                    `).join('');
                }
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
        // Always calculate final Fair Value dynamically based on active models and current weights
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

        let finalFv = null;
        let finalMos = null;

        if (totalWeight > 0) {
            finalFv = weightedSum / totalWeight;
            finalMos = ((finalFv - globalData.current_price) / globalData.current_price) * 100;
            // v47: Sync for reactive simulations
            globalData.fair_value = finalFv;
            globalData.margin_of_safety = finalMos;
        } else {
            // Fallback to backend static values if no active models are found
            finalFv = globalData.fair_value;
            finalMos = globalData.margin_of_safety;
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

        // --- Sync Profile & Metrics Table PEG with Card PEG ---
        const pegTableVal = document.getElementById('metric-val-peg');
        if (pegTableVal && currentPegToDisplay != null && !_simulating) {
            pegTableVal.textContent = currentPegToDisplay.toFixed(2);
        }
    };

    window.triggerRecalculate = updateFairValue;

    const inputSelectors = [
        'fcf-source', 'dcf-years-source', 'dcf-method-selector', 'input-exit-multiple', 'dcf-growth-1-3', 'dcf-growth-4-6', 'dcf-growth-7-8', 'dcf-growth-9-10', 'dcf-custom-wacc', 'dcf-custom-perp',
        'dcf-buyback-source', 'dcf-custom-buyback', 'relative-variant',
        'lynch-multiple-source', 'lynch-custom-mult', 'lynch-eps-source', 'lynch-custom-growth',
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

    // v272: DCF Growth Cascading Logic (-2% per phase)
    const setupDcfCascade = () => {
        const g13 = document.getElementById('dcf-growth-1-3');
        const g46 = document.getElementById('dcf-growth-4-6');
        const g78 = document.getElementById('dcf-growth-7-8');
        const g910 = document.getElementById('dcf-growth-9-10');

        // v277: Ripple only from 1-3Y to all others, and ONLY if targets are default/empty
        if (g13) {
            g13.addEventListener('input', () => {
                const val = parseLocaleFloat(g13.value);
                if (isNaN(val) || window._isApplyingOverrides) return;

                const pairs = [[g46, 2], [g78, 4], [g910, 6]];
                pairs.forEach(([target, diff]) => {
                    if (!target) return;
                    if (target.value === '' || target.dataset.isDefault === 'true') {
                        target.value = formatCleanInputVal(val - diff);
                        target.dataset.isDefault = 'true';
                        target.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                });
            });
        }

        // Mark as NOT default if the user manually types in any box
        [g46, g78, g910].forEach(target => {
            if (target) {
                target.addEventListener('keydown', () => {
                    target.dataset.isDefault = 'false';
                });
            }
        });

        // v272: Also trigger cascade when switching years to ensure newly shown fields are populated
        const yearsSrc = document.getElementById('dcf-years-source');
        if (yearsSrc) {
            yearsSrc.addEventListener('change', () => {
                if (g13 && g13.value !== '') {
                    g13.dispatchEvent(new Event('input', { bubbles: true }));
                }
            });
        }
    };
    setupDcfCascade();

    // --- Card-level Weights toggle for Relative Valuation ---
    const relModeCard = document.getElementById('rel-weight-mode-card');
    const relCWPanelCard = document.getElementById('rel-custom-weights-card');
    if (relModeCard) {
        relModeCard.onchange = () => {
            if (relCWPanelCard) relCWPanelCard.style.display = relModeCard.value === 'custom' ? 'block' : 'none';
            if (relModeCard.value === 'default') {
                window._relCustomWeights = null;
                updateAndSave();
            }
        };
    }
    const relApplyCard = document.getElementById('rel-apply-custom-card');
    if (relApplyCard) {
        relApplyCard.onclick = () => {
            const errEl = document.getElementById('rel-weight-error-card');
            const inputs = relCWPanelCard ? relCWPanelCard.querySelectorAll('input[type="number"]') : [];
            let customW = {};
            let total = 0;
            inputs.forEach(inp => {
                const key = inp.id.replace('rel-cw-card-', '');
                const v = parseFloat(inp.value) || 0;
                customW[key] = v / 100;
                total += v;
            });
            if (Math.abs(total - 100) > 1) {
                if (errEl) { errEl.textContent = `${total.toFixed(0)}% ≠ 100%`; errEl.style.display = 'inline'; }
                return;
            }
            if (errEl) errEl.style.display = 'none';
            window._relCustomWeights = customW;
            updateAndSave();
        };
    }

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
        ['lynch-eps-source', 'peg-eps-source'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = 'analyst';
        });
        const fcfSourceEl = document.getElementById('fcf-source');
        if (fcfSourceEl) fcfSourceEl.value = 'custom';
        const fcfMarginEl = document.getElementById('dcf-custom-fcf-margin');
        if (fcfMarginEl) fcfMarginEl.value = '';
        const fcfMarginGrowthEl = document.getElementById('dcf-custom-margin-growth');
        if (fcfMarginGrowthEl) fcfMarginGrowthEl.value = '0.2';
        const yearsSourceEl = document.getElementById('dcf-years-source');
        if (yearsSourceEl) yearsSourceEl.value = '10yr';

        try {
            // v305: Parallel fetch for valuation AND fresh overrides to prevent cross-device drift
            const [valRes, ovRes] = await Promise.all([
                fetch(`/api/valuation/${encodeURIComponent(query)}?t=${Date.now()}`),
                fetch(`/api/overrides?t=${Date.now()}`, { cache: 'no-store' })
            ]);

            if (!valRes.ok) throw new Error('Network response was not ok');

            const data = await valRes.json();
            const freshOverrides = await ovRes.json().catch(() => ({}));

            // Sync the global cache before rendering to ensure both mobile and desktop use same rules
            cachedOverrides = freshOverrides || {};

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

        // Save original peers before custom overrides (v307)
        if (data.company_profile && data.company_profile.competitor_metrics && !data.company_profile.original_competitor_metrics) {
            data.company_profile.original_competitor_metrics = JSON.parse(JSON.stringify(data.company_profile.competitor_metrics));
        }

        // Custom Peers Loader (v306)
        const savedPeers = localStorage.getItem('customPeers_' + data.ticker);
        if (savedPeers && data.company_profile) {
            try {
                const peersList = JSON.parse(savedPeers);
                data.company_profile.competitor_metrics = peersList;
                data.company_profile.competitors = peersList.map(p => p.ticker);
            } catch (e) {
                console.error("Error loading custom peers", e);
            }
        }

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

        // v72: Smart Anchor selection (Prioritize Adjusted EPS for Tech/Health)
        const isTech = (data.company_profile?.sector || '').toLowerCase().includes('technology') || 
                       (data.company_profile?.sector || '').toLowerCase().includes('communication') ||
                       (data.company_profile?.industry || '').toLowerCase().includes('software') ||
                       (data.company_profile?.industry || '').toLowerCase().includes('internet');
        const isHealth = (data.company_profile?.sector || '').toLowerCase().includes('healthcare');
        
        const anchorPEItem = data.buy_breakdown?.find(i => i.metric && i.metric.includes('P/E Ratio'));
        const anchorPEGItem = data.buy_breakdown?.find(i => i.metric === 'PEG Ratio');
        
        // Base EPS for simulation: Use Adjusted EPS for Tech/Health if available, else Trailing
        let baseEps = data.company_profile?.trailing_eps || 0;
        if ((isTech || isHealth) && data.company_profile?.adjusted_eps) {
            baseEps = data.company_profile.adjusted_eps;
        }

        window._simAnchors = {
            eps: (anchorPEItem && parseFloat(anchorPEItem.value) > 0) ? (data.current_price / parseFloat(anchorPEItem.value)) : (baseEps || 0),
            growth: (anchorPEGItem && parseFloat(anchorPEGItem.value) > 0 && anchorPEItem) ? (parseFloat(anchorPEItem.value) / parseFloat(anchorPEGItem.value)) : (data.company_profile?.revenue_growth || 10)
        };

        elements.name.textContent = data.name;
        elements.ticker.textContent = data.ticker;
        elements.currentPrice.textContent = formatCurrency(data.current_price);

        // Reset Simulate Price mode on new ticker load
        _simulating = false;
        _realApiPrice = data.current_price;
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
                fvContainer.insertAdjacentHTML('afterend', `<div id="company-desc-card" class="glass-card" style="margin-top: 15px; padding: 20px; border-left: 4px solid #38bdf8; position: relative;"></div>`);
                descCard = document.getElementById('company-desc-card');
            }

            let activeTab = 'overview';

            const renderCorporateBrief = (synthesisText, isLoadingAI = false) => {
                // v301: Smart client-side regex parser for the AI Synthesis sections
                const parseSynthesis = (text) => {
                    const sections = {
                        executiveSummary: "",
                        strategicStrengths: [],
                        vulnerabilitiesRisks: [],
                        latestMarketIntelligence: []
                    };
                    if (!text) return sections;
                    const parts = text.split(/\*\*(EXECUTIVE SUMMARY|SINTEZĂ EXECUTIVĂ|STRATEGIC STRENGTHS|PUNCTE FORTE STRATEGICE|VULNERABILITIES \& RISKS|VULNERABILITĂȚI ȘI RISCURI|LATEST MARKET INTELLIGENCE|ULTIMELE INFORMAȚII DE PIAȚĂ)\*\*/i);
                    for (let i = 1; i < parts.length; i += 2) {
                        const title = parts[i].trim().toUpperCase();
                        const content = parts[i+1] ? parts[i+1].trim() : "";
                        if (title === "EXECUTIVE SUMMARY" || title === "SINTEZĂ EXECUTIVĂ") {
                            sections.executiveSummary = content;
                        } else if (title === "STRATEGIC STRENGTHS" || title === "PUNCTE FORTE STRATEGICE") {
                            sections.strategicStrengths = content.split('\n')
                                .map(line => line.replace(/^•\s*/, '').trim())
                                .filter(Boolean);
                        } else if (title === "VULNERABILITIES & RISKS" || title === "VULNERABILITĂȚI ȘI RISCURI") {
                            sections.vulnerabilitiesRisks = content.split('\n')
                                .map(line => line.replace(/^•\s*/, '').trim())
                                .filter(Boolean);
                        } else if (title === "LATEST MARKET INTELLIGENCE" || title === "ULTIMELE INFORMAȚII DE PIAȚĂ") {
                            sections.latestMarketIntelligence = content.split('\n')
                                .map(line => line.replace(/^•\s*/, '').trim())
                                .filter(Boolean);
                        }
                    }
                    return sections;
                };

                const parsed = parseSynthesis(synthesisText);
                
                // Build Dynamic KPI Badges
                let kpiHtml = '';
                const pe = prof.trailing_pe || prof.current_pe;
                let netMargin = prof.net_margin || prof.operating_margin;
                if (netMargin != null) {
                    netMargin = netMargin / 100;
                }
                const deRatio = prof.debt_to_equity;
                
                if (pe != null && pe > 0) {
                    if (pe > 45) {
                        kpiHtml += `<span style="background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;">🔴 PE Premium (${pe.toFixed(1)}x)</span>`;
                    } else if (pe < 18) {
                        kpiHtml += `<span style="background: rgba(34, 197, 94, 0.12); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;">🟢 PE Atractiv (${pe.toFixed(1)}x)</span>`;
                    } else {
                        kpiHtml += `<span style="background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;">🟡 PE Moderat (${pe.toFixed(1)}x)</span>`;
                    }
                }
                if (netMargin != null) {
                    if (netMargin > 1.0) {
                        kpiHtml += `<span style="background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;" title="Câștig excepțional non-recurent ce depășește 100% din venituri.">⚠️ Profit Excepțional (${(netMargin * 100).toFixed(0)}%)</span>`;
                    } else if (netMargin > 0.20) {
                        kpiHtml += `<span style="background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;">💎 Marje Ridicate (${(netMargin * 100).toFixed(0)}%)</span>`;
                    } else if (netMargin < 0.05) {
                        kpiHtml += `<span style="background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;">⚠️ Marje Reduse (${(netMargin * 100).toFixed(0)}%)</span>`;
                    } else {
                        kpiHtml += `<span style="background: rgba(255, 255, 255, 0.05); color: rgba(255,255,255,0.7); border: 1px solid rgba(255, 255, 255, 0.1); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;">📊 Marje Sănătoase (${(netMargin * 100).toFixed(0)}%)</span>`;
                    }
                }
                if (deRatio != null) {
                    if (deRatio < 40) {
                        kpiHtml += `<span style="background: rgba(168, 85, 247, 0.12); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;">🛡️ Grad Îndatorare Sigur</span>`;
                    } else if (deRatio > 150) {
                        kpiHtml += `<span style="background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;">⚠️ Grad Îndatorare Ridicat (${deRatio.toFixed(0)}%)</span>`;
                    } else {
                        kpiHtml += `<span style="background: rgba(255, 255, 255, 0.05); color: rgba(255,255,255,0.7); border: 1px solid rgba(255, 255, 255, 0.1); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;">⚖️ Datorie Echilibrată</span>`;
                    }
                }

                // AI Semantic Insights Extraction (only if not loading/generating)
                if (!isLoadingAI) {
                    const synthText = (synthesisText || "").toLowerCase();
                    const hasPharma = /phase\s+[i|1|ii|2|iii|3]|clinical|fda|pdufa|pipeline|drug|vaccine|pharma|biotech|clinic|farmaceutic/i.test(synthText);
                    const hasMa = /acquire|acquisition|merger|takeover|bought|transaction|integration|achizi|fuzi/i.test(synthText);
                    const hasSegment = /segment|division|revenue share|growth driver|business unit|segmentation|diviz/i.test(synthText);
                    
                    if (hasPharma) {
                        kpiHtml += `<span class="insight-badge" style="background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px; animation: brief-pulse 2s infinite;" title="Pipeline clinic, decizie FDA sau fază de testare detectată.">🧪 Catalyst Clinic</span>`;
                    }
                    if (hasMa) {
                        kpiHtml += `<span class="insight-badge" style="background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;" title="Activitate M&A, fuziuni sau costuri de integrare detectate.">🤝 Tranzacție M&A</span>`;
                    }
                    if (hasSegment) {
                        kpiHtml += `<span class="insight-badge" style="background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; gap: 4px;" title="Analiză specifică pe segmente de activitate sau divizii.">📈 Focus pe Segmente</span>`;
                    }
                }

                let badgeHtml = '';
                if (isLoadingAI) {
                    badgeHtml = `<div id="ai-synthesis-badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); font-size: 0.6rem; padding: 3px 8px; border-radius: 20px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; animation: skeleton-pulse 1.5s infinite;">⏳ SE GENEREAZĂ ANALIZA AI...</div>`;
                } else if (synthesisText) {
                    badgeHtml = `<div id="ai-synthesis-badge" style="background: linear-gradient(135deg, #38bdf8, #818cf8); color: white; font-size: 0.6rem; padding: 3px 8px; border-radius: 20px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">✨ ANALIZĂ AI</div>`;
                }

                descCard.innerHTML = `
                    <style>
                        @keyframes brief-pulse {
                            0% { opacity: 0.8; }
                            50% { opacity: 1; transform: scale(1.01); }
                            100% { opacity: 0.8; }
                        }
                        @keyframes skeleton-pulse {
                            0% { opacity: 0.35; }
                            50% { opacity: 0.75; }
                            100% { opacity: 0.35; }
                        }
                        .brief-tab {
                            background: none;
                            border: none;
                            color: rgba(255,255,255,0.5);
                            padding: 8px 12px;
                            font-size: 0.85rem;
                            font-weight: 700;
                            cursor: pointer;
                            font-family: 'Outfit', sans-serif;
                            transition: all 0.2s ease;
                            opacity: 0.7;
                            position: relative;
                            white-space: nowrap;
                        }
                        .brief-tab:hover {
                            opacity: 1;
                            color: #38bdf8 !important;
                        }
                        .brief-tab.active {
                            opacity: 1;
                            color: #38bdf8 !important;
                            border-bottom: 2px solid #38bdf8 !important;
                        }
                        .brief-news-item {
                            background: rgba(255,255,255,0.02);
                            border: 1px solid rgba(255,255,255,0.05);
                            border-radius: 8px;
                            padding: 10px 12px;
                            margin-bottom: 8px;
                            transition: all 0.2s ease;
                        }
                        .brief-news-item:hover {
                            background: rgba(255,255,255,0.05);
                            border-color: rgba(56, 189, 248, 0.2);
                            transform: translateY(-1px);
                        }
                        .skeleton-text {
                            height: 12px;
                            background: rgba(255,255,255,0.05);
                            margin-bottom: 8px;
                            border-radius: 4px;
                            animation: skeleton-pulse 1.5s infinite;
                        }
                    </style>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <h3 style="font-size: 0.75rem; color: rgba(255,255,255,0.4); margin: 0; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 800; font-family: 'Outfit', sans-serif;">Rezumat Corporativ</h3>
                            ${badgeHtml}
                        </div>
                        <button id="copy-brief-btn" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 4px 8px; color: rgba(255,255,255,0.7); cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 0.72rem; transition: all 0.2s; font-family: 'Outfit', sans-serif;" title="Copiază rezumatul în clipboard">
                            <span style="font-size: 0.8rem;">📋</span> <span id="copy-brief-text">Copiază</span>
                        </button>
                    </div>
                    
                    <!-- KPI Row -->
                    <div id="brief-kpis" style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 15px;">
                        ${kpiHtml}
                    </div>
                    
                    <!-- Tabs Navigation -->
                    <div style="display: flex; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px; gap: 10px; overflow-x: auto; scrollbar-width: none;">
                        <button class="brief-tab ${activeTab === 'overview' ? 'active' : ''}" data-tab="overview">🏢 Prezentare Generală</button>
                        <button class="brief-tab ${activeTab === 'swot' ? 'active' : ''}" data-tab="swot">⚖️ Analiză SWOT</button>
                        <button class="brief-tab ${activeTab === 'news' ? 'active' : ''}" data-tab="news">📰 Informații de Piață</button>
                    </div>

                    <!-- Active Tab Content -->
                    <div id="brief-panel-content" style="font-size: 0.9rem; line-height: 1.6; color: rgba(255,255,255,0.85); max-height: 250px; overflow-y: auto; padding-right: 6px; font-family: 'Outfit', sans-serif;"></div>
                `;

                const renderActivePanel = () => {
                    const panel = document.getElementById('brief-panel-content');
                    if (!panel) return;
                    
                    if (activeTab === 'overview') {
                        if (isLoadingAI) {
                            panel.innerHTML = `
                                <div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 8px; color: white;">
                                    ${prof.name || 'Compania'} este clasificată în sectorul <span style="color:#38bdf8;">${prof.sector || 'N/A'}</span>, industria <span style="color:#38bdf8;">${prof.industry || 'N/A'}</span>.
                                </div>
                                <div style="margin-top: 10px;">
                                    <div class="skeleton-text" style="width: 100%;"></div>
                                    <div class="skeleton-text" style="width: 95%;"></div>
                                    <div class="skeleton-text" style="width: 90%;"></div>
                                    <div class="skeleton-text" style="width: 60%;"></div>
                                </div>
                            `;
                        } else {
                            panel.innerHTML = `
                                <div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 8px; color: white;">
                                    ${prof.name || 'Compania'} este clasificată în sectorul <span style="color:#38bdf8;">${prof.sector || 'N/A'}</span>, industria <span style="color:#38bdf8;">${prof.industry || 'N/A'}</span>.
                                </div>
                                <p style="margin: 0; color: rgba(255,255,255,0.8); line-height: 1.6; text-align: justify;">
                                    ${parsed.executiveSummary || prof.business_summary || 'Nu există nicio descriere succintă disponibilă.'}
                                </p>
                            `;
                        }
                    } else if (activeTab === 'swot') {
                        if (isLoadingAI) {
                            panel.innerHTML = `
                                <div style="display: flex; flex-direction: row; flex-wrap: wrap; gap: 15px; width: 100%;">
                                    <div style="flex: 1 1 280px; min-width: 250px;">
                                        <h4 style="color: #4ade80; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Puncte Forte Strategice</h4>
                                        <div class="skeleton-text" style="width: 100%; height: 35px; border-radius: 6px;"></div>
                                        <div class="skeleton-text" style="width: 100%; height: 35px; border-radius: 6px;"></div>
                                    </div>
                                    <div style="flex: 1 1 280px; min-width: 250px;">
                                        <h4 style="color: #f87171; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Vulnerabilități și Riscuri</h4>
                                        <div class="skeleton-text" style="width: 100%; height: 35px; border-radius: 6px;"></div>
                                        <div class="skeleton-text" style="width: 100%; height: 35px; border-radius: 6px;"></div>
                                    </div>
                                </div>
                            `;
                        } else {
                            const strengthsHtml = parsed.strategicStrengths.length > 0 
                                ? parsed.strategicStrengths.map(s => `
                                    <div style="display: flex; gap: 10px; margin-bottom: 8px; align-items: flex-start; background: rgba(34, 197, 94, 0.04); border: 1px solid rgba(34, 197, 94, 0.1); padding: 8px 12px; border-radius: 6px;">
                                        <span style="color: #4ade80; font-weight: bold; font-size: 0.9rem; flex-shrink:0;">✔️</span>
                                        <span style="color: rgba(255,255,255,0.85); font-size: 0.8rem;">${s}</span>
                                    </div>`).join('')
                                : '<div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; padding: 10px; font-style:italic;">Operațiuni comerciale diversificate.</div>';
                                
                            const risksHtml = parsed.vulnerabilitiesRisks.length > 0 
                                ? parsed.vulnerabilitiesRisks.map(r => `
                                    <div style="display: flex; gap: 10px; margin-bottom: 8px; align-items: flex-start; background: rgba(239, 68, 68, 0.04); border: 1px solid rgba(239, 68, 68, 0.1); padding: 8px 12px; border-radius: 6px;">
                                        <span style="color: #f87171; font-weight: bold; font-size: 0.9rem; flex-shrink:0;">⚠️</span>
                                        <span style="color: rgba(255,255,255,0.85); font-size: 0.8rem;">${r}</span>
                                    </div>`).join('')
                                : '<div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; padding: 10px; font-style:italic;">Expunere la ciclurile de piață globale.</div>';

                            panel.innerHTML = `
                                <div style="display: flex; flex-direction: row; flex-wrap: wrap; gap: 15px; width: 100%;">
                                    <div style="flex: 1 1 280px; min-width: 250px;">
                                        <h4 style="color: #4ade80; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Puncte Forte Strategice</h4>
                                        ${strengthsHtml}
                                    </div>
                                    <div style="flex: 1 1 280px; min-width: 250px;">
                                        <h4 style="color: #f87171; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Vulnerabilități și Riscuri</h4>
                                        ${risksHtml}
                                    </div>
                                </div>
                            `;
                        }
                    } else if (activeTab === 'news') {
                        if (isLoadingAI) {
                            panel.innerHTML = `
                                <div class="brief-news-item"><div class="skeleton-text" style="width: 80%;"></div><div class="skeleton-text" style="width: 50%;"></div></div>
                                <div class="brief-news-item"><div class="skeleton-text" style="width: 75%;"></div><div class="skeleton-text" style="width: 45%;"></div></div>
                            `;
                        } else if (parsed.latestMarketIntelligence.length > 0) {
                            panel.innerHTML = parsed.latestMarketIntelligence.map(item => {
                                const match = item.match(/^(.*?)\s*\(Source:\s*(.*?)\)$/i);
                                const title = match ? match[1] : item;
                                const source = match ? match[2] : "Știri de Piață";
                                
                                return `
                                    <div class="brief-news-item">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; gap: 10px;">
                                            <span style="background: rgba(56, 189, 248, 0.1); color: #38bdf8; font-size: 0.58rem; padding: 2px 6px; border-radius: 4px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.3px;">${source}</span>
                                        </div>
                                        <div style="color: rgba(255,255,255,0.9); font-size: 0.8rem; line-height: 1.4;">${title}</div>
                                    </div>
                                `;
                            }).join('');
                        } else {
                            panel.innerHTML = '<div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; padding: 20px; text-align: center; font-style:italic;">Nu există știri recente sau evoluții de piață globale.</div>';
                        }
                    }
                };
                
                // Draw first panel
                renderActivePanel();
                
                // Setup Click Handlers for Tabs
                const tabs = descCard.querySelectorAll('.brief-tab');
                tabs.forEach(t => {
                    t.onclick = () => {
                        tabs.forEach(btn => btn.classList.remove('active'));
                        t.classList.add('active');
                        activeTab = t.getAttribute('data-tab');
                        renderActivePanel();
                    };
                });
                
                // Copy brief handler
                const copyBtn = document.getElementById('copy-brief-btn');
                const copyText = document.getElementById('copy-brief-text');
                if (copyBtn) {
                    copyBtn.onclick = () => {
                        const textToCopy = synthesisText || (prof.name + ' - ' + (prof.business_summary || ''));
                        navigator.clipboard.writeText(textToCopy).then(() => {
                            copyText.textContent = 'Copiat!';
                            copyBtn.style.background = 'rgba(34, 197, 94, 0.15)';
                            copyBtn.style.color = '#4ade80';
                            copyBtn.style.borderColor = 'rgba(34, 197, 94, 0.3)';
                            setTimeout(() => {
                                copyText.textContent = 'Copiază';
                                copyBtn.style.background = 'rgba(255,255,255,0.05)';
                                copyBtn.style.color = 'rgba(255,255,255,0.7)';
                                copyBtn.style.borderColor = 'rgba(255,255,255,0.1)';
                            }, 2000);
                        });
                    };
                }
            };

            // Determine if the loaded synthesis is just a fallback (either empty, or containing our specific fallback marker)
            const isFallback = !data.company_overview_synthesis || 
                               data.company_overview_synthesis.includes("AI Insights generation is active") ||
                               data.company_overview_synthesis.includes("Generarea analizei AI este activă");

            // Fast rendering of local heuristic fallback initially. If fallback, show loading state
            renderCorporateBrief(data.company_overview_synthesis, isFallback);

            // Fetch high-fidelity synthesis in the background if it's the heuristic fallback
            if (isFallback) {
                fetch(`/api/valuation/${encodeURIComponent(data.ticker)}/synthesis`)
                    .then(response => {
                        if (!response.ok) throw new Error('Failed to fetch synthesis');
                        return response.json();
                    })
                    .then(synthData => {
                        if (synthData && synthData.company_overview_synthesis) {
                            data.company_overview_synthesis = synthData.company_overview_synthesis;
                            renderCorporateBrief(data.company_overview_synthesis, false);
                        }
                    })
                    .catch(err => {
                        console.error('[Synthesis Async] Error loading AI synthesis:', err);
                        // Disable loading state and fallback permanently to heuristics
                        renderCorporateBrief(data.company_overview_synthesis, false);
                    });
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
        currentPiotroskiBreakdown = data.piotroski_breakdown || (data.piotroski && data.piotroski.breakdown) || [];

        updateScoreUI(data.health_score_total, 'health-score-circle', 'health-score-fill');
        updateScoreUI(data.good_to_buy_total, 'buy-score-circle', 'buy-score-fill');
        updatePiotroskiUI(data.piotroski ? data.piotroski.score : data.piotroski_score);

        // Bind click handlers on score rows (must be done here, after data is loaded)
        // v70: Use dynamic closures to ensure modals always show CURRENT simulated data
        const healthRow = document.getElementById('health-score-row') || document.getElementById('health-score-circle')?.closest('.score-row');
        if (healthRow) {
            healthRow.style.cursor = 'pointer';
            healthRow.onclick = () => {
                renderScoreBreakdown('Company Health Breakdown', globalData.health_score_total, currentHealthBreakdown);
            };
        }
        const buyRow = document.getElementById('buy-score-row') || document.getElementById('buy-score-circle')?.closest('.score-row');
        if (buyRow) {
            buyRow.style.cursor = 'pointer';
            buyRow.onclick = () => {
                renderScoreBreakdown('Good to Buy Score Breakdown', globalData.good_to_buy_total, currentBuyBreakdown);
            };
        }

        // Piotroski F-Score Click Binding
        const pioRow = document.getElementById('piotroski-score-row');
        if (pioRow) {
            pioRow.style.cursor = 'pointer';
            pioRow.onclick = () => {
                const pScore = data.piotroski ? data.piotroski.score : data.piotroski_score;
                renderPiotroskiBreakdown(pScore, currentPiotroskiBreakdown);
            };
        }

        // Rule of 40 UI Update & Click Binding
        updateRule40UI(data.rule_of_40);
        const rule40Row = document.getElementById('rule40-score-row');
        if (rule40Row) {
            rule40Row.style.cursor = 'pointer';
            rule40Row.onclick = () => {
                renderRule40Breakdown(globalData.rule_of_40);
            };
        }

        // UPDATED: Sync both MOS and PEG to the Score Breakdown dynamically

        // v289: The Unstoppable DCF Growth Logic (DOM Scraping -> Object Logic -> Flat Fallback)
        window.getDcfGrowthDefault = (data) => {
            if (!data) return 10.0;
            
            // Try to parse from the rev_estimates array (strictly FY 1 and FY 2)
            const rList = data.rev_estimates || [];
            const ests = rList.filter(e => e && e.status !== 'reported' && e.growth != null);
            if (ests.length >= 2) {
                const g1 = parseFloat(ests[0].growth);
                const g2 = parseFloat(ests[1].growth);
                if (!isNaN(g1) && !isNaN(g2)) {
                    return Math.round(((g1 + g2) / 2) * 1000) / 10;
                }
            } else if (ests.length === 1) {
                const g1 = parseFloat(ests[0].growth);
                if (!isNaN(g1)) return Math.round(g1 * 1000) / 10;
            }
            
            if (data.company_profile && data.company_profile.revenue_growth != null) {
                return Math.round(data.company_profile.revenue_growth * 1000) / 10;
            }
            
            return 8.0;
        };

        const targetGrowth = window.getDcfGrowthDefault(data);
        const g13 = document.getElementById('dcf-growth-1-3');
        if (g13) {
            const hadOverrides = (cachedOverrides[data.ticker] && cachedOverrides[data.ticker].inputs && cachedOverrides[data.ticker].inputs['dcf-growth-1-3']);
            if (!hadOverrides) {
                g13.value = formatCleanInputVal(targetGrowth);
                g13.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }

        // Initialize inputs to company's defaults before applying overrides
        const dcf = data.formula_data?.dcf;
        if (dcf) {
            const waccInput = document.getElementById('dcf-custom-wacc');
            if (waccInput) {
                const defaultWacc = dcf.discount_rate_applied || (dcf.discount_rate ? dcf.discount_rate * 100 : 9.0);
                waccInput.value = formatCleanInputVal(defaultWacc);
            }
            const perpInput = document.getElementById('dcf-custom-perp');
            if (perpInput) {
                const defaultPerp = dcf.perpetual_growth ? dcf.perpetual_growth * 100 : 2.5;
                perpInput.value = formatCleanInputVal(defaultPerp);
            }
            const exitInput = document.getElementById('input-exit-multiple');
            if (exitInput) {
                const defaultExit = data.dcf_assumptions?.recommended_exit_multiple || 15.0;
                exitInput.value = formatCleanInputVal(defaultExit);
            }
        }

        // Restore overrides BEFORE first updateFairValue
        const hadOverrides = applyOverrides(currentTicker);
        updateFairValue();

        document.querySelectorAll('.valuation-toggle').forEach(toggle => {
            toggle.onchange = updateAndSave;
        });

        const renderProfileSection = () => {
            const pBody = document.getElementById('profile-body');
            if (pBody && data.company_profile) {
                const prof = data.company_profile;

                // UPDATED: Replaced bad *100 formatting with safe formatSafePct
                const current_price = data.current_price || 0;
                const non_gaap_pe = (current_price > 0 && prof.adjusted_eps > 0) ? current_price / prof.adjusted_eps : null;

                const metricRow = (label, value, subtext = '', customStyle = '') => {
                    const id = 'metric-val-' + label.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
                    return `
                    <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04); align-items: center;">
                        <div style="display: flex; flex-direction: column;">
                            <span style="color: rgba(255,255,255,0.5); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">${label}</span>
                            ${subtext ? `<span style="font-size: 0.7rem; color: rgba(255,255,255,0.3); margin-top: 2px;">${subtext}</span>` : ''}
                        </div>
                        <span id="${id}" style="font-weight: 600; font-size: 0.95rem; color: white; ${customStyle} text-align: right; max-width: 60%; word-wrap: break-word; transition: color 0.2s;">${value}</span>
                    </div>
                    `;
                };

                pBody.innerHTML = `
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 2.5rem;">
                        <!-- Column 1: Company -->
                        <div class="profile-section">
                            <div style="font-size: 0.8rem; color: var(--text-main); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid rgba(255,255,255,0.1); font-weight: 700;">Company Summary</div>
                            <div style="display: flex; flex-direction: column;">
                                ${metricRow('Industry', prof.industry, prof.sector)}
                                ${metricRow('Market Cap', formatBigNumber(prof.market_cap, '$'))}
                                ${metricRow('Shares Out.', formatBigNumber(prof.shares_outstanding, ''))}
                                ${metricRow('Buyback Rate', prof.buyback_rate != null ? (prof.buyback_rate > 0 ? '+' : '') + formatSafePct(prof.buyback_rate) : 'N/A', '', prof.buyback_rate < 0 ? 'color: #ef4444;' : '')}
                                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04); align-items: center;">
                                    <span style="color: rgba(255,255,255,0.5); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">Competitors</span>
                                    <div style="display: flex; align-items: center; gap: 8px; text-align: right; max-width: 65%;">
                                        <span style="font-weight: 600; font-size: 0.95rem; color: white; word-wrap: break-word;">${prof.competitors && prof.competitors.length ? prof.competitors.join(', ') : 'None'}</span>
                                        ${prof.competitor_metrics && prof.competitor_metrics.length > 0 ? `<button id="compare-peers-btn" class="peer-btn" style="margin:0;">📊 PEERS</button>` : ''}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Column 2: Valuation -->
                        <div class="profile-section">
                            <div style="font-size: 0.8rem; color: var(--text-main); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid rgba(255,255,255,0.1); font-weight: 700;">Valuation & Earnings</div>
                            <div style="display: flex; flex-direction: column;">
                                ${metricRow('P/E (Trailing)', prof.trailing_pe ? prof.trailing_pe.toFixed(2) + 'x' : 'N/A')}
                                ${metricRow('P/E Non-GAAP', non_gaap_pe ? non_gaap_pe.toFixed(2) + 'x' : 'N/A')}
                                ${metricRow('5Y Avg. P/E', prof.historic_pe ? prof.historic_pe.toFixed(2) + 'x' : 'N/A')}
                                ${metricRow('PE FWD', prof.fwd_pe ? prof.fwd_pe.toFixed(2) + 'x' : 'N/A')}
                                ${metricRow('EPS Diluted', prof.trailing_eps ? '$' + prof.trailing_eps.toFixed(2) : 'N/A')}
                                ${metricRow('EPS Non-GAAP', prof.adjusted_eps ? '$' + prof.adjusted_eps.toFixed(2) : 'N/A')}
                                ${metricRow('FWD EPS', prof.fwd_eps ? '$' + prof.fwd_eps.toFixed(2) : 'N/A')}
                                ${metricRow('PEG', prof.peg_ratio ? prof.peg_ratio.toFixed(2) : 'N/A')}
                                ${metricRow('P/S', prof.ps_ratio ? prof.ps_ratio.toFixed(2) + 'x' : 'N/A')}
                                ${metricRow('P/S FWD', prof.fwd_ps ? prof.fwd_ps.toFixed(2) + 'x' : 'N/A')}
                                ${metricRow('P/FCF', prof.pfcf_ratio ? prof.pfcf_ratio.toFixed(2) + 'x' : 'N/A')}
                            </div>
                        </div>

                        <!-- Column 3: Dividends -->
                        <div class="profile-section">
                            <div style="font-size: 0.8rem; color: var(--text-main); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid rgba(255,255,255,0.1); font-weight: 700;">Dividends</div>
                            <div style="display: flex; flex-direction: column;">
                                ${metricRow('Dividend Yield', formatSafePct(prof.dividend_yield))}
                                ${metricRow('Payout Ratio', formatSafePct(prof.payout_ratio), '', prof.payout_ratio > 0.80 ? 'color: var(--danger);' : '')}
                                ${metricRow('Div. Streak', prof.dividend_streak != null ? prof.dividend_streak + ' Years' : 'N/A')}
                                ${metricRow('5Y Div Growth', formatSafePct(prof.dividend_cagr_5y))}
                            </div>
                        </div>
                    </div>
                `;

                if(document.getElementById('compare-peers-btn')) {
                    document.getElementById('compare-peers-btn').onclick = () => renderComparisonModal(prof);
                }
            }
        };
        window._renderProfile = renderProfileSection;
        renderProfileSection();

        // --- ADDITIONAL SECTIONS ---
        const trendsBody = document.getElementById('trends-body');
        const anchors = data.historical_anchors;

        if (trendsBody) {
            if (anchors && anchors.length > 0) {
                // v44: Transposed Table with Sparklines
                const config = [
                    { label: 'Year', key: 'year', isHeader: true },
                    { label: 'Revenue (B)', key: 'revenue_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'revenue_b' },
                    { label: 'EPS (GAAP)', key: 'eps', formatter: v => (v != null) ? '$' + v.toFixed(2) : 'N/A', sparkKey: 'eps' },
                    { label: 'FCF (B)', key: 'fcf_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'fcf_b' },
                    { label: 'Net Margin', key: 'net_margin_pct', formatter: v => (v != null) ? v : 'N/A', sparkKey: 'net_margin_pct' },
                    { label: 'Cash (B)', key: 'cash_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'cash_b' },
                    { label: 'Debt (B)', key: 'total_debt_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'total_debt_b' },
                    { label: 'Current Ratio', key: 'current_ratio', formatter: v => (v != null) ? v.toFixed(2) : 'N/A', sparkKey: 'current_ratio' },
                    { label: 'Shares (B)', key: 'shares_out_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'shares_out_b' },
                    { label: 'ROIC', key: 'roic_pct', formatter: v => (v != null) ? v : 'N/A', sparkKey: 'roic_pct' }
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
                    const sparkHtml = !isYear ? generateSparkline(anchors.map(a => a[metric.key]).reverse()) : '';
                    
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

        renderHistoricalCharts(data);
        renderAnalystEstimatesInline(data.ticker);

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
        'dcf-growth-1-3', 'dcf-growth-4-6', 'dcf-growth-7-8', 'dcf-growth-9-10', 'dcf-custom-wacc', 'dcf-custom-perp', 'dcf-custom-fcf-margin', 'dcf-custom-margin-growth',
        'dcf-buyback-source', 'dcf-custom-buyback', 'relative-variant',
        'lynch-multiple-source', 'lynch-custom-mult', 'lynch-eps-source', 'lynch-custom-growth',
        'peg-eps-source', 'peg-custom-growth', 'peg-mode'
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

        // v299: Lock cascade during load
        window._isApplyingOverrides = true;

        // Apply inputs
        Object.entries(inputs).forEach(([id, val]) => {
            const el = document.getElementById(id);
            if (el) {
                let cleanVal = val;
                if (el.type === 'number' && (id.includes('growth') || id.includes('perp') || id.includes('wacc') || id.includes('mult') || id.includes('dcf-growth-'))) {
                    const parsed = parseFloat(val);
                    if (!isNaN(parsed)) {
                        cleanVal = parsed % 1 === 0 ? parsed.toString() : parsed.toFixed(1);
                    }
                }
                el.value = cleanVal;
                // Show/hide custom input containers based on select values
                if (id === 'fcf-source' || id === 'dcf-buyback-source' || id === 'lynch-multiple-source' || id === 'lynch-eps-source' || id === 'peg-eps-source') {
                   const ciId = id === 'fcf-source' ? 'dcf-custom-inputs' : 
                               id === 'dcf-buyback-source' ? 'dcf-buyback-custom-inputs' :
                               id === 'lynch-multiple-source' ? 'lynch-custom-multiple-inputs' :
                               id === 'lynch-eps-source' ? 'lynch-custom-inputs' : 'peg-custom-inputs';
                   const ci = document.getElementById(ciId);
                   if (ci) {
                       if (ciId === 'lynch-custom-inputs' || ciId === 'peg-custom-inputs' || ciId === 'lynch-custom-multiple-inputs') {
                           ci.style.display = val === 'custom' ? 'grid' : 'none';
                       } else {
                           ci.style.display = val === 'custom' ? 'flex' : 'none';
                       }
                   }
                }
                if (id === 'dcf-method-selector') switchDCFMethod(val);
            }
        });

        // Apply toggles
        Object.entries(toggles).forEach(([id, checked]) => {
            const el = document.getElementById(id);
            if (el) el.checked = checked;
        });

        window._isApplyingOverrides = false;
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
            if (rowExit) rowExit.style.display = 'grid';
        } else {
            if (rowPerp) rowPerp.style.display = 'grid';
            if (rowExit) rowExit.style.display = 'none';
        }
        updateFairValue();
    };
    window.switchDCFMethod = switchDCFMethod;

    const resetMethodDefaults = (method) => {
        if (!globalData || !currentTicker) return;
        
        // 1. Clear overrides for this specific method
        const ov = cachedOverrides[currentTicker];
        if (ov && ov.inputs) {
            const idsToReset = {
                dcf: ['fcf-source', 'dcf-years-source', 'dcf-method-selector', 'input-exit-multiple', 'dcf-growth-1-3', 'dcf-growth-4-6', 'dcf-growth-7-8', 'dcf-growth-9-10', 'dcf-custom-wacc', 'dcf-custom-perp', 'dcf-custom-fcf-margin', 'dcf-custom-margin-growth', 'dcf-buyback-source', 'dcf-custom-buyback'],
                relative: ['relative-variant', 'rel-weight-mode-card'],
                peter_lynch: ['lynch-multiple-source', 'lynch-custom-mult', 'lynch-eps-source', 'lynch-custom-growth'],
                peg: ['peg-eps-source', 'peg-custom-growth', 'peg-mode']
            };
            
            (idsToReset[method] || []).forEach(id => {
                delete ov.inputs[id];
            });
            
            saveOverridesToServer(currentTicker);
        }
        
        // 2. Re-apply baseline overrides (if any left)
        applyOverrides(currentTicker);

        // 3. FORCE re-population of specific fields for THIS method
        if (method === 'dcf') {
            // Reset Dropdowns
            ['fcf-source', 'dcf-buyback-source', 'dcf-method-selector', 'dcf-years-source'].forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.value = (id === 'fcf-source') ? 'custom' : 
                               (id === 'dcf-years-source') ? '10yr' :
                               (id === 'dcf-buyback-source') ? 'none' : 'perpetual';
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
            
            // v286: Use global unified logic
            const targetGrowth = window.getDcfGrowthDefault(globalData);

            const g13 = document.getElementById('dcf-growth-1-3');
            if (g13) {
                g13.value = formatCleanInputVal(targetGrowth);
                // Reset 'isDefault' markers to allow fresh cascade
                const g46 = document.getElementById('dcf-growth-4-6');
                const g78 = document.getElementById('dcf-growth-7-8');
                const g910 = document.getElementById('dcf-growth-9-10');
                if (g46) { g46.value = ''; g46.dataset.isDefault = 'true'; }
                if (g78) { g78.value = ''; g78.dataset.isDefault = 'true'; }
                if (g910) { g910.value = ''; g910.dataset.isDefault = 'true'; }
                g13.dispatchEvent(new Event('input', { bubbles: true }));
            }
            const wacc = document.getElementById('dcf-custom-wacc');
            if (wacc) wacc.value = '9';
            const perp = document.getElementById('dcf-custom-perp');
            if (perp) perp.value = '2.5';
            const fcfMargin = document.getElementById('dcf-custom-fcf-margin');
            if (fcfMargin) fcfMargin.value = '';
            const fcfMarginGrowth = document.getElementById('dcf-custom-margin-growth');
            if (fcfMarginGrowth) fcfMarginGrowth.value = '0.2';
            
            switchDCFMethod('perpetual');
        } else if (method === 'relative') {
            const relVar = document.getElementById('relative-variant');
            if (relVar) relVar.value = 'peers';
            const relWeight = document.getElementById('rel-weight-mode-card');
            if (relWeight) relWeight.value = 'default';
        } else if (method === 'peter_lynch') {
            const lMult = document.getElementById('lynch-multiple-source');
            if (lMult) lMult.value = 'pe20';
            const lEps = document.getElementById('lynch-eps-source');
            if (lEps) lEps.value = 'analyst';
        } else if (method === 'peg') {
            const pEps = document.getElementById('peg-eps-source');
            if (pEps) pEps.value = 'analyst';
            const pMode = document.getElementById('peg-mode');
            if (pMode) pMode.value = 'standard';
        }
        
        updateFairValue();
    };

    document.querySelectorAll('.reset-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const button = e.target.closest('.reset-btn');
            if (!button) return;
            const method = button.getAttribute('data-method');
            if (confirm(`Reset ${method.toUpperCase()} to defaults?`)) {
                resetMethodDefaults(method);
            }
        });
    });

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

        // v298: Dynamic Timeline Expansion
        // We look at analyst estimates and if we see a year that's NOT in our chart labels, we add it.
        const labels = [...(hd.years || [])];
        const epsDataRawBase = [...(hd.eps || [])];
        const revDataRawBase = [...(hd.revenue || [])];
        const fcfDataRawBase = [...(hd.fcf || [])];
        const sharesDataRawBase = [...(hd.shares || [])];

        const allEst = [...(data.eps_estimates || []), ...(data.rev_estimates || [])];
        const newYears = [];
        allEst.forEach(est => {
            if (est.status === 'estimate') {
                const yrMatch = est.period.match(/\d{4}/);
                if (yrMatch) {
                    const yrStr = yrMatch[0];
                    const label = yrStr + ' (Est)';
                    if (!labels.includes(label) && !labels.includes(yrStr)) {
                        if (!newYears.includes(yrStr)) newYears.push(yrStr);
                    }
                }
            }
        });
        
        newYears.sort().forEach(yr => {
            labels.push(yr + ' (Est)');
            epsDataRawBase.push(0);
            revDataRawBase.push(0);
            fcfDataRawBase.push(0);
            sharesDataRawBase.push(sharesDataRawBase.length > 0 ? sharesDataRawBase[sharesDataRawBase.length - 1] : 0);
        });

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
            
            // Build custom legend
            const legendEl = document.getElementById('legend-rev-fcf');
            if (legendEl) {
                legendEl.innerHTML = `
                    <div class="legend-item"><span class="legend-dot" style="background:#38bdf8"></span> Revenue</div>
                    <div class="legend-item"><span class="legend-dot" style="background:#10b981"></span> FCF</div>
                `;
            }

            chartRevFcf = new Chart(ctxRevFcf, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'Revenue ($B)',
                            data: revDataRawBase.map(v => v ? +(v / 1e9).toFixed(2) : 0),
                            backgroundColor: bgColors('rgba(56, 189, 248, 1)', 0.7, 0.3),
                            borderColor: 'rgba(56, 189, 248, 1)',
                            borderWidth: 1,
                            borderRadius: 4,
                            order: 2
                        },
                        {
                            label: 'FCF ($B)',
                            data: fcfDataRawBase.map(v => v ? +(v / 1e9).toFixed(2) : 0),
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
                        legend: { display: false },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        x: { 
                            ticks: { 
                                color: '#94a3b8', 
                                font: { size: window.innerWidth < 768 ? 9 : 11 },
                                maxRotation: 45,
                                autoSkip: true
                            }, 
                            grid: { color: 'rgba(148,163,184,0.1)' } 
                        },
                        y: { 
                            ticks: { color: '#94a3b8', font: { size: 10 }, callback: v => formatLargeNumber(v, '$') }, 
                            grid: { color: 'rgba(148,163,184,0.1)' } 
                        }
                    }
                }
            });
        }

        // ── Chart 2: EPS & Shares Outstanding (Dual Axis) ──
        const ctxEps = document.getElementById('chart-eps-shares');
        if (ctxEps) {
            if (chartEpsShares) chartEpsShares.destroy();

            // v279: Link graph to Historical Anchors table (strictly GAAP Diluted EPS for history)
            const anchors = data.historical_anchors || [];
            const gaapMap = {};
            anchors.forEach(a => {
                if (a.year) gaapMap[String(a.year)] = a.eps;
            });

            const epsDataRaw = hd.eps || [];
            const epsData = labels.map((l, i) => {
                const yearStr = String(l).replace(' (Est)', '');
                if (gaapMap[yearStr] !== undefined) return gaapMap[yearStr];
                return epsDataRawBase[i] || 0;
            });
            
            const sharesData = sharesDataRawBase.map(v => v ? +(v / 1e9).toFixed(3) : 0);

            // Build custom legend
            const legendEl = document.getElementById('legend-eps-shares');
            if (legendEl) {
                legendEl.innerHTML = `
                    <div class="legend-item"><span class="legend-dot" style="background:#a855f7"></span> EPS</div>
                    <div class="legend-item"><span class="legend-dot" style="background:#fbbf24"></span> Shares (B)</div>
                `;
            }

            chartEpsShares = new Chart(ctxEps, {
                type: 'bar', 
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
                        legend: { display: false },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        x: { 
                            ticks: { 
                                color: '#94a3b8', 
                                font: { size: window.innerWidth < 768 ? 9 : 11 },
                                maxRotation: 45,
                                autoSkip: true
                            }, 
                            grid: { color: 'rgba(148,163,184,0.1)' } 
                        },
                        y:  { 
                            position: 'left',  
                            ticks: { color: '#a855f7', font: { size: 10 }, callback: v => formatLargeNumber(v, '$') }, 
                            grid: { color: 'rgba(148,163,184,0.1)' }, 
                        },
                        y1: { 
                            position: 'right', 
                            ticks: { color: '#fbbf24', font: { size: 10 }, callback: v => formatLargeNumber(v) }, 
                            grid: { drawOnChartArea: false }, 
                        }
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
            if (document.getElementById('pt-avg')) document.getElementById('pt-avg').textContent = (pt.avg != null) ? `$${parseFloat(pt.avg).toFixed(2)}` : '--';
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
                const medianRating = rec.median_label;
                let ratingLabel = 'N/A';
                
                // v279: Convert numerical rating to descriptive label (1.0 = Strong Buy, 5.0 = Strong Sell)
                if (typeof medianRating === 'number') {
                    if (medianRating <= 1.5) ratingLabel = 'Strong Buy';
                    else if (medianRating <= 2.5) ratingLabel = 'Buy';
                    else if (medianRating <= 3.5) ratingLabel = 'Hold';
                    else if (medianRating <= 4.5) ratingLabel = 'Sell';
                    else ratingLabel = 'Strong Sell';
                } else {
                    ratingLabel = medianRating || 'N/A';
                }
                
                statusElem.textContent = ratingLabel;
                
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
            eItems.forEach((item, idx) => {
                if (!item) return;
                const pLabel = item.period || '--';
                const isAnchor = item.status === 'reported';
                const aVal = (item.avg != null) ? formatLargeNumber(parseFloat(item.avg), '$') : '--';
                let gVal = isAnchor ? '' : '--';
                
                if (!isAnchor) {
                    if (item.status === 'reported' && item.surprise_pct != null) {
                        gVal = (parseFloat(item.surprise_pct) * 100).toFixed(1) + '%';
                    } else if (item.growth != null) {
                        gVal = (parseFloat(item.growth) * 100).toFixed(1) + '%';
                    }
                }
                
                const sColor = isAnchor ? 'white' : getColor(item);
                const weight = item.status === 'reported' ? 'bold' : 'normal';
                const labelColor = isAnchor ? 'white' : (item.status === 'reported' ? '#4ade80' : 'inherit');
                const valColor = isAnchor ? 'white' : 'inherit';
                const estVal = item.num_estimates != null ? item.num_estimates : '--';
                
                if (eBody) eBody.innerHTML += `<tr><td style="padding:4px 0;color:${labelColor};">${pLabel}</td><td style="text-align:right;color:${valColor};">${aVal}</td><td style="text-align:right;color:${sColor};font-weight:${weight};">${gVal}</td></tr>`;
            });

            const rItems = data.rev_estimates || [];
            rItems.forEach((item, idx) => {
                if (!item) return;
                const pLabel = item.period || '--';
                const isAnchor = item.status === 'reported';
                const aVal = (item.avg != null) ? formatLargeNumber(parseFloat(item.avg), '$') : '--';
                let gVal = isAnchor ? '' : '--';
                
                if (!isAnchor && item.growth != null) {
                    gVal = (parseFloat(item.growth) * 100).toFixed(1) + '%';
                }
                
                const sColor = isAnchor ? 'white' : getColor(item);
                const weight = item.status === 'reported' ? 'bold' : 'normal';
                const labelColor = isAnchor ? 'white' : (item.status === 'reported' ? '#4ade80' : 'inherit');
                const valColor = isAnchor ? 'white' : 'inherit';
                
                if (rBody) rBody.innerHTML += `<tr><td style="padding:4px 0;color:${labelColor};">${pLabel}</td><td style="text-align:right;color:${valColor};">${aVal}</td><td style="text-align:right;color:${sColor};font-weight:${weight};">${gVal}</td></tr>`;
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

            // Sync analyst estimates data to globalData
            if (globalData && globalData.ticker && globalData.ticker.toUpperCase() === ticker.toUpperCase()) {
                globalData.rev_estimates = rItems;
                globalData.eps_estimates = eItems;
                
                const g13 = document.getElementById('dcf-growth-1-3');
                if (g13) {
                    const hadOverrides = (cachedOverrides[globalData.ticker] && cachedOverrides[globalData.ticker].inputs && cachedOverrides[globalData.ticker].inputs['dcf-growth-1-3']);
                    if (!hadOverrides) {
                        const targetGrowth = window.getDcfGrowthDefault(globalData);
                        g13.value = formatCleanInputVal(targetGrowth);
                        // Cascade to other inputs
                        g13.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
                
                // Re-calculate all fair values to reflect the fresh consensus growth
                updateFairValue();
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
                                <span style="font-size: 0.75rem; font-weight: 800; margin-right: 4px; color: ${(data.piotroski?.score >= 7) ? 'var(--accent)' : (data.piotroski?.score >= 4 ? '#fbbf24' : (data.piotroski?.score == null ? 'var(--text-muted)' : 'var(--danger)'))}">
                                    ${data.piotroski?.score != null ? data.piotroski.score : '--'}
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
    document.body.addEventListener('click', (e) => {
        const btn = e.target.closest('.modal-trigger');
        if (!btn) return;
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
                const prof = globalData ? globalData.company_profile : {};
                title.textContent = 'Discounted Cash Flow';

                const method = document.getElementById('dcf-method-selector')?.value || 'perpetual';
                const renderDCFView = (yp) => {
                    const dataObj = method === 'multiple' ? d.dcf_exit_multiple : d.dcf_perpetual;
                    if (!dataObj) return '<p style="color:var(--text-muted);">Data not available for this method.</p>';
                    
                    const fcfYears = dataObj.fcf_projections || [];
                    const sensMatrix = method === 'perpetual' ? (dataObj.sensitivity_matrix || []) : [];
                    
                    const baseFcf = d.fcf || 0;
                    const baseRevenue = globalData.revenue || 0;
                    const customMarginEl = document.getElementById('dcf-custom-fcf-margin');
                    const customMargin = (customMarginEl && customMarginEl.value !== '') ? parseLocaleFloat(customMarginEl.value) : null;
                    let startingFcfMargin = 0.10;
                    if (customMargin !== null && !isNaN(customMargin)) {
                        startingFcfMargin = customMargin / 100;
                    } else if (baseRevenue > 0) {
                        startingFcfMargin = baseFcf / baseRevenue;
                    }
                    const customMarginGrowthEl = document.getElementById('dcf-custom-margin-growth');
                    const customMarginGrowth = (customMarginGrowthEl && customMarginGrowthEl.value !== '') ? parseLocaleFloat(customMarginGrowthEl.value) / 100 : 0.002;

                    let tableHTML = `<table style="width:100%; border-collapse:collapse; margin-top:20px; font-size: 0.95rem;">
                                        <tr style="border-bottom:1px solid rgba(255,255,255,0.2);">
                                            <th style="text-align:left; padding:8px 0; color:white;">Year</th>
                                            <th style="text-align:right; padding:8px 0; color:white;">Projected FCF</th>
                                            <th style="text-align:right; padding:8px 0; color:white;">FCF Margin</th>
                                        </tr>`;
                    fcfYears.forEach((val, i) => {
                        const yearMargin = startingFcfMargin + ((i + 1) * customMarginGrowth);
                        tableHTML += `<tr>
                                        <td style="padding:6px 0; color:white;">Year ${i+1}</td>
                                        <td style="text-align:right; color:white;">${fmtBig(val)}</td>
                                        <td style="text-align:right; color:var(--accent); font-weight:600;">${fmtPct(yearMargin)}</td>
                                      </tr>`;
                    });
                    tableHTML += `</table>`;

                    const tvLabel = method === 'perpetual' ? `Terminal Value (${fmtPct(dataObj.perpetual_growth_rate)} Growth)` : `Terminal Value (${dataObj.exit_multiple}x Multiple)`;

                    let matrixHTML = '';
                    if (method === 'perpetual' && sensMatrix.length > 0) {
                        matrixHTML = `<div style="margin-top: 25px;">
                            <h4 style="margin-bottom:15px; font-size:1rem; text-transform:uppercase; letter-spacing:1px; color:white; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:5px;">DCF Sensitivity Matrix</h4>
                            <div style="overflow-x:auto;">
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
                        matrixHTML += `</table></div></div>`;
                    }

                    return `
                        <div style="background:rgba(255,255,255,0.02); padding:20px; border-radius:8px; border:1px solid rgba(255,255,255,0.05); margin-bottom:20px;">
                            <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:var(--text-muted);">Starting Growth Rate:</span><span style="font-weight:500; color:${(Array.isArray(d.eps_growth_applied) ? d.eps_growth_applied[0] : d.eps_growth_applied) < 0 ? 'var(--danger)' : 'white'};">${fmtPct(Array.isArray(d.eps_growth_applied) ? d.eps_growth_applied[0] : d.eps_growth_applied)}</span></div>
                            <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:var(--text-muted);">Discount Rate (Applied):</span><span style="font-weight:500; color:white;">${fmtPct(dataObj.discount_rate)}</span></div>
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
                title.textContent = '📊 Relative Valuation — Triangulation';

                // --- Determine which metrics are active based on sector weights ---
                const SECTOR_WEIGHTS = {
                    'Technology': { PE: 0.35, EV_EBITDA: 0.50, PS: 0.15 },
                    'Information Technology': { PE: 0.35, EV_EBITDA: 0.50, PS: 0.15 },
                    'Technology_Growth': { PE: 0.00, EV_EBITDA: 0.20, PS: 0.80 },
                    'Financial Services': { PE: 0.40, PB: 0.60 },
                    'Financials': { PE: 0.40, PB: 0.60 },
                    'Industrials': { PE: 0.20, EV_EBITDA: 0.80 },
                    'Energy': { PE: 0.20, EV_EBITDA: 0.80 },
                    'Consumer Defensive': { PE: 0.50, EV_EBITDA: 0.30, PS: 0.20 },
                    'Consumer Staples': { PE: 0.50, EV_EBITDA: 0.30, PS: 0.20 },
                    'Consumer Cyclical': { PE: 0.35, EV_EBITDA: 0.35, PS: 0.30 },
                    'Consumer Discretionary': { PE: 0.35, EV_EBITDA: 0.35, PS: 0.30 },
                    'Healthcare': { PE: 0.35, EV_EBITDA: 0.40, PS: 0.25 },
                    'Health Care': { PE: 0.35, EV_EBITDA: 0.40, PS: 0.25 },
                    'Communication Services': { PE: 0.35, EV_EBITDA: 0.40, PS: 0.25 },
                    'Utilities': { PE: 0.50, EV_EBITDA: 0.50 },
                    'Basic Materials': { PE: 0.25, EV_EBITDA: 0.75 },
                    'Materials': { PE: 0.25, EV_EBITDA: 0.75 },
                    'Real Estate': { PE: 0.00, P_FFO: 0.80, P_AFFO: 0.20 },
                    'Default': { PE: 0.40, EV_EBITDA: 0.40, PS: 0.20 }
                };
                const sn = r.sector || 'Default';
                let defaultWeights = SECTOR_WEIGHTS[sn] || SECTOR_WEIGHTS['Default'];
                if ((sn === 'Technology' || sn === 'Information Technology') && 
                    ((r.company_eps || 0) <= 0 || (r.company_fcf_share || 0) <= 0)) {
                    defaultWeights = SECTOR_WEIGHTS['Technology_Growth'];
                }
                
                // Active metric keys for this sector
                const activeKeys = Object.keys(defaultWeights).filter(k => (defaultWeights[k] || 0) > 0);
                
                // Label map
                const LABEL = { PE: 'P/E', PFCF: 'P/FCF', PS: 'P/S', PB: 'P/B', EV_EBITDA: 'EV/EBITDA', P_FFO: 'P/FFO', P_AFFO: 'P/AFFO' };
                const peerKeyMap = { PE: 'pe_ratio', PFCF: 'pfcf_ratio', PS: 'ps_ratio', PB: 'price_to_book', EV_EBITDA: 'ev_to_ebitda' };

                // --- Competitor Table ---
                const peers = (globalData.company_profile && globalData.company_profile.competitor_metrics) || [];

                const getMedian = (arr) => {
                    const sorted = arr.filter(x => x != null && !isNaN(x)).sort((a, b) => a - b);
                    if (sorted.length === 0) return null;
                    const mid = Math.floor(sorted.length / 2);
                    return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
                };

                const getMean = (arr) => {
                    const valid = arr.filter(x => x != null && !isNaN(x));
                    if (valid.length === 0) return null;
                    return valid.reduce((sum, v) => sum + v, 0) / valid.length;
                };

                const dynamicMedians = {
                    PE: getMedian(peers.map(p => p.pe_ratio)),
                    PFCF: getMedian(peers.map(p => p.pfcf_ratio)),
                    PS: getMedian(peers.map(p => p.ps_ratio)),
                    PB: getMedian(peers.map(p => p.price_to_book)),
                    EV_EBITDA: getMedian(peers.map(p => p.ev_to_ebitda))
                };

                const dynamicMeans = {
                    PE: getMean(peers.map(p => p.pe_ratio)),
                    PFCF: getMean(peers.map(p => p.pfcf_ratio)),
                    PS: getMean(peers.map(p => p.ps_ratio)),
                    PB: getMean(peers.map(p => p.price_to_book)),
                    EV_EBITDA: getMean(peers.map(p => p.ev_to_ebitda))
                };

                let peerTableHTML = '';
                if (peers.length > 0) {
                    peerTableHTML = `
                    <h4 style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;">Peer Benchmarks</h4>
                    <div style="overflow-x:auto; margin-bottom:1.5rem;">
                    <table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
                        <thead>
                            <tr style="border-bottom:1px solid rgba(255,255,255,0.15);">
                                <th style="text-align:left; padding:8px 6px; color:white;">Ticker</th>
                                ${activeKeys.map(k => `<th style="text-align:right; padding:8px 6px; color:white;">${LABEL[k] || k}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            <!-- Target Company Row -->
                            <tr style="border-bottom:1px solid rgba(255,255,255,0.1); background: rgba(40, 199, 111, 0.05);">
                                <td style="padding:6px; color:#28c76f; font-weight:700;">${(globalData.ticker || 'TARGET').toUpperCase()}</td>
                                ${activeKeys.map(k => {
                                    let val = null;
                                    if (k === 'PE') {
                                        const adjEps = globalData.company_profile && globalData.company_profile.adjusted_eps;
                                        const curPrice = globalData.current_price || 0;
                                        if (adjEps && adjEps > 0 && curPrice > 0) {
                                            val = curPrice / adjEps;
                                        } else {
                                            val = (globalData.company_profile && (globalData.company_profile.trailing_pe || globalData.company_profile.current_pe));
                                        }
                                    }
                                    else if (k === 'PS') val = (globalData.company_profile && globalData.company_profile.ps_ratio);
                                    else if (k === 'PB') val = (globalData.company_profile && globalData.company_profile.price_to_book);
                                    else if (k === 'EV_EBITDA') val = (r && r.company_ev_ebitda);
                                    
                                    return `<td style="text-align:right; padding:6px; color:#28c76f; font-weight:700;">${val != null ? val.toFixed(1) + 'x' : '—'}</td>`;
                                }).join('')}
                            </tr>
                            
                            <!-- Peers Rows -->
                            ${peers.map(p => `
                                <tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
                                    <td style="padding:6px; color:white; font-weight:600;">${p.ticker}</td>
                                    ${activeKeys.map(k => {
                                        const dk = peerKeyMap[k];
                                        const val = dk ? p[dk] : null;
                                        return `<td style="text-align:right; padding:6px; color:var(--text-main);">${val != null ? val.toFixed(1) + 'x' : '—'}</td>`;
                                    }).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr style="border-top:1px solid rgba(255,255,255,0.15);">
                                <td style="padding:8px 6px; color:white; font-weight:700;">Median</td>
                                ${activeKeys.map(k => {
                                    const v = dynamicMedians[k] ?? r['median_peer_' + k.toLowerCase()];
                                    return `<td style="text-align:right; padding:8px 6px; color:white; font-weight:700;">${v != null ? v.toFixed(1) + 'x' : '—'}</td>`;
                                }).join('')}
                            </tr>
                        </tfoot>
                    </table>
                    </div>`;
                }

                // --- Implied Values & Weights ---
                const variantEl = document.getElementById('relative-variant');
                const variant = variantEl ? variantEl.value : 'peers';
                
                const getBenchmark = (key) => {
                    const medMap = {
                        PE: dynamicMedians.PE ?? r.median_peer_pe,
                        PFCF: dynamicMedians.PFCF ?? r.median_peer_pfcf,
                        PS: dynamicMedians.PS ?? r.median_peer_ps,
                        PB: dynamicMedians.PB ?? r.median_peer_pb,
                        EV_EBITDA: dynamicMedians.EV_EBITDA ?? r.median_peer_ev_ebitda,
                        P_FFO: dynamicMedians.PE ?? r.median_peer_pe,
                        P_AFFO: dynamicMedians.PFCF ?? r.median_peer_pfcf
                    };
                    const meanMap = {
                        PE: dynamicMeans.PE ?? r.mean_peer_pe,
                        PFCF: dynamicMeans.PFCF ?? r.mean_peer_pfcf,
                        PS: dynamicMeans.PS ?? r.mean_peer_ps,
                        PB: dynamicMeans.PB ?? r.mean_peer_pb,
                        EV_EBITDA: dynamicMeans.EV_EBITDA ?? r.mean_peer_ev_ebitda,
                        P_FFO: dynamicMeans.PE ?? r.mean_peer_pe,
                        P_AFFO: dynamicMeans.PFCF ?? r.mean_peer_pfcf
                    };
                    const sp500Map = { PE: r.sp500_pe, PFCF: r.sp500_pfcf, PS: r.sp500_ps, PB: r.sp500_pb, EV_EBITDA: r.sp500_ev_ebitda, P_FFO: r.sp500_pe, P_AFFO: r.sp500_pfcf };
                    const defaults = { PE: 20, PFCF: 20, PS: 2, PB: 2, EV_EBITDA: 12, P_FFO: 15, P_AFFO: 15 };
                    if (variant === 'peers') return medMap[key] || defaults[key];
                    if (variant === 'average') return meanMap[key] || defaults[key];
                    return sp500Map[key] || defaults[key];
                };

                const getImplied = (key, bench) => {
                    const eps = r.company_eps || 0;
                    const fcfS = r.company_fcf_share || 0;
                    const salesS = r.company_sales_share || 0;
                    const bookS = r.company_book_share || 0;
                    const ebitda = globalData.ebitda || 0;
                    const debt = globalData.total_debt || 0;
                    const cash = globalData.total_cash || 0;
                    const shares = (globalData.company_profile && globalData.company_profile.shares_outstanding) || 1;
                    
                    if (key === 'PE' || key === 'P_FFO') return eps * bench;
                    if (key === 'PFCF' || key === 'P_AFFO') return fcfS * bench;
                    if (key === 'PS') return salesS * bench;
                    if (key === 'PB') return bookS * bench;
                    if (key === 'EV_EBITDA') {
                        const ev = ebitda * bench;
                        return shares > 0 ? (ev - debt + cash) / shares : 0;
                    }
                    return 0;
                };

                let breakdownRows = '';
                activeKeys.forEach(k => {
                    const bench = getBenchmark(k);
                    const implied = getImplied(k, bench);
                    const w = defaultWeights[k] || 0;
                    const safeImpl = implied > 0 ? implied : 0;
                    const implColor = safeImpl > 0 ? 'white' : 'var(--text-muted)';
                    breakdownRows += `
                        <tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
                            <td style="padding:8px 6px; color:var(--text-main);">${LABEL[k]}</td>
                            <td style="text-align:right; padding:8px 6px; color:var(--text-main);">${(bench || 0).toFixed(1)}x</td>
                            <td style="text-align:right; padding:8px 6px; color:${implColor}; font-weight:600;">${safeImpl > 0 ? '$' + fmt(safeImpl) : 'N/A'}</td>
                            <td style="text-align:right; padding:8px 6px; color:var(--accent); font-weight:700;" class="rel-weight-cell" data-key="${k}">${(w * 100).toFixed(0)}%</td>
                        </tr>`;
                });

                // Compute initial weighted FV for the modal display
                let _initSum = 0, _initTot = 0;
                activeKeys.forEach(k => {
                    const b = getBenchmark(k);
                    const impl = getImplied(k, b);
                    const w = defaultWeights[k] || 0;
                    if (w > 0 && impl > 0) { _initSum += impl * w; _initTot += w; }
                });
                const modalFV = _initTot > 0 ? _initSum / _initTot : 0;
                const modalFVColor = modalFV > (globalData.current_price || 0) ? 'var(--accent)' : 'var(--danger)';

                html = `
                    ${peerTableHTML}

                    <h4 style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;">Implied Values & Weights</h4>
                    <table style="width:100%; border-collapse:collapse; font-size:0.8rem; margin-bottom:1rem;">
                        <thead>
                            <tr style="border-bottom:1px solid rgba(255,255,255,0.15);">
                                <th style="text-align:left; padding:8px 6px; color:white;">Metric</th>
                                <th style="text-align:right; padding:8px 6px; color:white;">Benchmark</th>
                                <th style="text-align:right; padding:8px 6px; color:white;">Implied FV</th>
                                <th style="text-align:right; padding:8px 6px; color:white;">Weight</th>
                            </tr>
                        </thead>
                        <tbody>${breakdownRows}</tbody>
                    </table>

                    <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-top:1px solid rgba(255,255,255,0.1);">
                        <span style="font-size:0.85rem; color:white; font-weight:600;">Weighted Fair Value</span>
                        <span id="rel-modal-fv" style="font-size:1.2rem; font-weight:800; color:${modalFVColor};">$${fmt(modalFV)}</span>
                    </div>
                    <p style="font-size:0.7rem; color:var(--text-muted); margin-top:8px; font-style:italic;">
                        Weights can be adjusted via the card's "Weights" selector on the main dashboard.
                    </p>
                `;

                body.innerHTML = html;
                modal.style.display = 'flex';
                return;
            } else if (model === 'peter_lynch' && currentFormulaData.peter_lynch) {
                const p = currentFormulaData.peter_lynch;
                title.textContent = '📊 Forward Multiple — Data Transparency';
                const epsLabel = p.valuation_eps !== p.trailing_eps ? 'EPS Base (Normalized)' : 'Trailing EPS (GAAP)';
                html = row(epsLabel, '$' + fmt(p.valuation_eps || p.trailing_eps))
                     + row('Growth Estimate', fmtPct(p.dynamic_growth != null ? p.dynamic_growth : p.eps_growth_estimated))
                     + row('Forward EPS (3Y Projection)', '$' + fmt(p.dynamic_fwd_eps != null ? p.dynamic_fwd_eps : p.fwd_eps))
                     + row('Fair Value (PE 20)', '$' + fmt(p.dynamic_fv != null ? p.dynamic_fv : p.fair_value_pe_20));
            } else if (model === 'peg' && currentFormulaData.peg) {
                const g = currentFormulaData.peg;
                title.textContent = '📊 PEG Valuation — Data Transparency';
                const periodLabel = g.eps_growth_period || '2Y EPS CAGR';
                html = row('Current P/E (Adj.)', g.current_pe ? g.current_pe.toFixed(2) + 'x' : 'N/A')
                     + row('Growth Estimate', fmtPct(g.dynamic_growth != null ? g.dynamic_growth : g.eps_growth_estimated))
                     + row('Current PEG', g.dynamic_peg ? g.dynamic_peg.toFixed(2) + 'x' : (g.current_peg ? g.current_peg.toFixed(2) + 'x' : 'N/A'))
                     + row('Industry PEG', g.industry_peg ? g.industry_peg.toFixed(2) + 'x' : 'N/A')
                     + row('Fair Value', '$' + fmt(g.dynamic_fv != null ? g.dynamic_fv : g.fair_value))
                     + row('Margin of Safety', (() => { const cp = globalData.current_price; const fv = (g.dynamic_fv != null ? g.dynamic_fv : g.fair_value); if (fv != null && cp > 0) { const mos = (fv - cp) / cp; return fmtPct(mos); } return 'N/A'; })());
            } else {
                title.textContent = 'Data Transparency';
                html = '<p style="color:var(--text-muted);">No data available for this model.</p>';
            }

            body.innerHTML = html;
            modal.style.display = 'flex';
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

        // Build header - 3-column grid to center the total and align with X
        const displayTitle = title.replace(' Breakdown', '');
        let html = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding-bottom:5px; gap:15px; flex-wrap:nowrap;">
                <h3 style="margin:0; font-size:1.05rem; color:white; font-weight:800; white-space:nowrap;">${displayTitle}</h3>
                
                <div style="display:flex; align-items:baseline; gap:6px; flex-shrink:0;">
                    <span style="font-size:0.75rem; color:var(--text-muted); font-weight:600; text-transform:uppercase;">Total:</span>
                    <span style="font-size:1.3rem; font-weight:900; color:white;">${scoreVal}/${totalMax}</span>
                </div>
            </div>
        `;

        // Build rows - Grid: Label (flex) | Value (fixed) | Dot+Pts (fixed)
        breakdown.forEach(item => {
            let label = (item.metric || item.name || 'Unknown Metric');
            if (!label.includes('(adj.)')) {
                label = label.split(' (')[0];
            }
            
            const pts = (item.points_awarded !== undefined) ? item.points_awarded : (item.points || 0);
            const maxPts = item.max_points || 0;
            const pct = maxPts > 0 ? (pts / maxPts) : 0;

            // Dot color
            let dotColor = 'var(--danger)';
            let ptsColor = 'var(--danger)';
            if (pct >= 0.99) { dotColor = 'var(--accent)'; ptsColor = 'var(--accent)'; }
            else if (pct >= 0.4) { dotColor = '#fbbf24'; ptsColor = '#fbbf24'; }

            html += `
                <div style="display:grid; grid-template-columns: 1fr auto auto; align-items:center; padding:10px 0; border-top:1px solid rgba(255,255,255,0.04); gap:15px;">
                    <div style="font-weight:600; font-size:0.88rem; color:white; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${label}</div>
                    <div style="font-weight:700; font-size:0.9rem; color:rgba(255,255,255,0.85); text-align:right; font-family:monospace; min-width:60px;">${item.value || 'N/A'}</div>
                    <div style="display:flex; align-items:center; gap:8px; justify-content:flex-end; min-width:65px;">
                        <span style="width:8px; height:8px; border-radius:50%; background:${dotColor}; display:inline-block; flex-shrink:0;"></span>
                        <span style="font-weight:800; font-size:0.85rem; color:${ptsColor}; white-space:nowrap; font-family: 'Outfit', sans-serif;">${pts}/${maxPts}</span>
                    </div>
                </div>
            `;
        });

        if (titleEl) titleEl.textContent = '';
        body.innerHTML = html;
        modal.style.display = 'flex';
    };

    // ── Piotroski F-Score Breakdown Modal ──────────────────────
    function renderPiotroskiBreakdown(totalScore, breakdown) {
        const modal = document.getElementById('score-modal');
        const body = document.getElementById('score-modal-body-content');
        const titleEl = document.getElementById('score-modal-title');
        if (!modal || !body) return;

        if (!breakdown || breakdown.length === 0) {
            if (titleEl) titleEl.textContent = 'Piotroski F-Score';
            body.innerHTML = '<p style="color:var(--text-muted);">No Piotroski data available for this ticker.</p>';
            modal.style.display = 'flex';
            return;
        }

        const scoreVal = (totalScore != null && totalScore !== 'N/A') ? totalScore : '?';
        let html = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding-bottom:5px; gap:15px;">
                <h3 style="margin:0; font-size:1.05rem; color:white; font-weight:800;">Piotroski F-Score</h3>
                <div style="display:flex; align-items:baseline; gap:6px;">
                    <span style="font-size:0.75rem; color:var(--text-muted); font-weight:600; text-transform:uppercase;">Total:</span>
                    <span style="font-size:1.3rem; font-weight:900; color:white;">${scoreVal}/9</span>
                </div>
            </div>
        `;

        let lastGroup = '';
        breakdown.forEach(item => {
            // Group header
            const group = item.group || '';
            if (group && group !== lastGroup) {
                lastGroup = group;
                html += `<div style="margin-top:12px; margin-bottom:6px; font-size:0.75rem; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px;">${group}</div>`;
            }

            const label = item.criterion || item.name || 'Unknown';
            const passed = item.passed;
            const dotColor = passed === true ? 'var(--accent)' : (passed === false ? 'var(--danger)' : 'var(--text-muted)');
            const statusText = passed === true ? '✓ Pass' : (passed === false ? '✗ Fail' : '— N/A');
            const statusColor = passed === true ? 'var(--accent)' : (passed === false ? 'var(--danger)' : 'var(--text-muted)');

            html += `
                <div style="display:grid; grid-template-columns: 1fr auto auto; align-items:center; padding:8px 0; border-top:1px solid rgba(255,255,255,0.04); gap:15px;">
                    <div style="font-weight:600; font-size:0.85rem; color:white; overflow:hidden; text-overflow:ellipsis;">${label}</div>
                    <div style="font-weight:700; font-size:0.85rem; color:rgba(255,255,255,0.7); text-align:right; font-family:monospace; min-width:80px;">${item.value || 'N/A'}</div>
                    <div style="display:flex; align-items:center; gap:8px; justify-content:flex-end; min-width:60px;">
                        <span style="width:8px; height:8px; border-radius:50%; background:${dotColor}; display:inline-block; flex-shrink:0;"></span>
                        <span style="font-weight:800; font-size:0.85rem; color:${statusColor}; white-space:nowrap;">${statusText}</span>
                    </div>
                </div>
            `;
        });

        if (titleEl) titleEl.textContent = '';
        body.innerHTML = html;
        modal.style.display = 'flex';
    };

    // COLLAPSIBLE METHOD CARDS Accordion logic
    document.querySelectorAll('.collapsible-trigger').forEach(trigger => {
        trigger.addEventListener('click', () => {
            const cardId = trigger.getAttribute('data-card');
            const card = document.getElementById(`${cardId}-card`);
            if (card) {
                card.classList.toggle('collapsed');
                
                // Save collapsed state to localStorage
                const collapsedStates = JSON.parse(localStorage.getItem('method_cards_collapsed') || '{}');
                collapsedStates[cardId] = card.classList.contains('collapsed');
                localStorage.setItem('method_cards_collapsed', JSON.stringify(collapsedStates));
            }
        });
        
        // Restore collapsed state on load
        const cardId = trigger.getAttribute('data-card');
        const card = document.getElementById(`${cardId}-card`);
        if (card) {
            const collapsedStates = JSON.parse(localStorage.getItem('method_cards_collapsed') || '{}');
            if (collapsedStates[cardId]) {
                card.classList.add('collapsed');
            }
        }
    });

    // COLLAPSIBLE DETAILS Accordion logic inside cards
    document.querySelectorAll('.details-toggle-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            btn.classList.toggle('active');
            const content = btn.nextElementSibling;
            if (content) {
                content.classList.toggle('collapsed');
            }
        });
    });


});
