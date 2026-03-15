document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('search-btn');
    const tickerInput = document.getElementById('ticker-input');

    // Dashboard elements
    const dashboard = document.getElementById('dashboard');
    const loadingState = document.getElementById('loading-state');

    // Modal elements
    const viewDataBtns = document.querySelectorAll('.modal-trigger');
    const dataModal = document.getElementById('data-modal');
    const closeModal = document.getElementById('close-modal');
    const modalBodyContent = document.getElementById('modal-body-content');

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

    // Watchlist State (Load initially from localStorage for responsiveness, then sync)
    let watchlist = JSON.parse(localStorage.getItem('fairValueWatchlist')) || [];

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

    const analyzeTicker = async (queryParam) => {
        const query = (queryParam && typeof queryParam === 'string') ? queryParam : tickerInput.value.trim();
        if (!query) return;

        // Reset all specific UI custom filter dropdowns and hide custom inputs
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

        // Reset all method selectors to defaults when a new ticker is analyzed
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

        // UI Reset
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
        currentFormulaData = data.formula_data;
        currentTicker = data.ticker;

        elements.name.textContent = data.name;
        elements.ticker.textContent = data.ticker;
        elements.currentPrice.textContent = formatCurrency(data.current_price);

        updateWatchlistButtonState();

        // Display Estimated Fair Value - Text stays neutral
        elements.fairValue.textContent = formatCurrency(data.fair_value);

        // Display Margin of Safety - Button turns Red or Green
        if (data.margin_of_safety != null) {
            elements.marginSafety.textContent = `${formatPercent(data.margin_of_safety)} Margin of Safety`;
            if (data.margin_of_safety > 0) {
                elements.marginSafety.style.color = 'var(--accent)';
                elements.marginSafety.style.background = 'rgba(16, 185, 129, 0.2)';
            } else {
                elements.marginSafety.style.color = 'var(--danger)';
                elements.marginSafety.style.background = 'rgba(239, 68, 68, 0.2)';
            }
        } else {
            elements.marginSafety.textContent = 'N/A';
        }

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
                statusElem.style.color = "var(--accent)"; // Green
            } else if (diffPct <= -0.05) {
                statusElem.textContent = "Overvalued";
                statusElem.style.color = "var(--danger)"; // Red
            } else {
                statusElem.textContent = "Fair Valued";
                statusElem.style.color = "#fbbf24"; // Amber/Yellow
            }
        };

        setValuationStatus(data.dcf_value, data.current_price, 'dcf-status', 'dcf-value');
        
        // Populate DCF Card MOS and Price
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

        setValuationStatus(data.relative_value, data.current_price, 'relative-status', 'relative-value');

        // Update Dashboard Scores UI
        const updateScoreUI = (scoreVal, circleId, fillId) => {
            const circle = document.getElementById(circleId);
            const fill = document.getElementById(fillId);
            if (!circle || !fill) return;

            // Reset classes
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

            // Animate number
            circle.textContent = scoreVal;
            // Animate bar width
            setTimeout(() => {
                fill.style.width = `${scoreVal}%`;
            }, 50);

            // Apply color coding
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

        const updateInsightsAndScores = (newMos) => {
            if (!currentBuyBreakdown) return;

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

                if (typeof data.buy_score === 'number') {
                    updateScoreUI(data.buy_score, 'buy-score-circle', 'buy-score-fill');
                }
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

        // Forward Multiple Updates (formerly Peter Lynch)
        const lynchStatus = document.getElementById('lynch-status');
        const lynchFairValue = document.getElementById('lynch-fair-value');

        // Helper to calculate DCF locally (with optional share buyback rate)
        const calcLocalDcf = (fcf, growth, wacc, perp, shares, cash, debt, buybackRate = 0) => {
            if (!fcf || !shares || shares <= 0) return null;
            let pv = 0;
            let f = fcf;
            for (let i = 1; i <= 5; i++) {
                f *= (1 + growth);
                pv += f / Math.pow(1 + wacc, i);
            }
            const tv = (f * (1 + perp)) / (wacc - perp);
            const pvTv = tv / Math.pow(1 + wacc, 5);
            const ev = pv + pvTv;
            const eqVal = ev + (cash || 0) - (debt || 0);
            if (eqVal <= 0) return null;
            // Apply buyback: shares reduce by buybackRate%/yr compounded over 5 years
            const effectiveShares = shares * Math.pow(1 - (buybackRate || 0), 5);
            return eqVal / (effectiveShares > 0 ? effectiveShares : shares);
        };

        // Logic for Dynamic Recalculation
        const updateFairValue = () => {
            if (!currentFormulaData) return;
            const prof = data.company_profile;

            // DCF Logic
            let dcfVal = null;
            if (currentFormulaData.dcf) {
                const fcfSourceEl = document.getElementById('fcf-source');
                const fcfSource = fcfSourceEl ? fcfSourceEl.value : 'analyst';
                const dcfInputs = document.getElementById('dcf-custom-inputs');
                if (dcfInputs) dcfInputs.style.display = fcfSource === 'custom' ? 'flex' : 'none';

                // Buyback
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
                        dcfVal = currentFormulaData.dcf.intrinsic_value;
                    } else {
                        // Re-calculate with buyback rate applied on top of analyst FCF value
                        const g = currentFormulaData.dcf.eps_growth_estimated || 0.10;
                        const w = waccInput && waccInput.value ? parseFloat(waccInput.value)/100 : (currentFormulaData.dcf.discount_rate || 0.09);
                        const p = currentFormulaData.dcf.perpetual_growth || 0.02;
                        dcfVal = calcLocalDcf(baseFcf, g, w, p, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate);
                    }
                } else if (fcfSource === 'historical') {
                    const hg = prof.historic_fcf_growth != null ? prof.historic_fcf_growth : 0.05;
                    dcfVal = calcLocalDcf(baseFcf, hg, 0.09, 0.02, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate);
                } else if (fcfSource === 'custom') {
                    const g = parseFloat(document.getElementById('dcf-custom-growth').value) / 100 || 0.15;
                    const w = parseFloat(document.getElementById('dcf-custom-wacc').value) / 100 || 0.09;
                    const p = parseFloat(document.getElementById('dcf-custom-perp').value) / 100 || 0.025;
                    dcfVal = calcLocalDcf(baseFcf, g, w, p, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate);
                }
            }
            setValuationStatus(dcfVal, data.current_price, 'dcf-status', 'dcf-value');

            // Update Labels with Periods
            const pegGrowthLabel = document.querySelector('label[for="peg-custom-growth"]');
            if (pegGrowthLabel && currentFormulaData.peg.eps_growth_period) {
                pegGrowthLabel.textContent = `Growth Rate (${currentFormulaData.peg.eps_growth_period}) (%)`;
            }
            const lynchGrowthLabel = document.querySelector('label[for="lynch-custom-growth"]');
            if (lynchGrowthLabel) {
                lynchGrowthLabel.textContent = `3Y Est. Growth Rate`;
            }
            const dcfGrowthLabel = document.querySelector('label[for="dcf-custom-growth"]');
            if (dcfGrowthLabel) {
                dcfGrowthLabel.textContent = `Growth Rate (%)`;
            }

            // PEG Logic
            let pegVal = null;
            let pegMos = null;
            if (currentFormulaData.peg) {
                const pegSrcEl = document.getElementById('peg-eps-source');
                const pegSrc = pegSrcEl ? pegSrcEl.value : 'analyst';
                const pegInputs = document.getElementById('peg-custom-inputs');
                if (pegInputs) pegInputs.style.display = pegSrc === 'custom' ? 'flex' : 'none';

                let usedGrowth = currentFormulaData.peg.eps_growth_estimated || 0;
                if (pegSrc === 'custom') {
                    usedGrowth = (parseFloat(document.getElementById('peg-custom-growth').value) || 20) / 100;
                }

                const currentPe = currentFormulaData.peg.current_pe || (data.current_price / (data.company_profile.trailing_eps || 1));
                const industryPeg = currentFormulaData.peg.industry_peg;

                if (usedGrowth > 0 && currentPe > 0 && industryPeg > 0) {
                    const dynamicCompanyPeg = currentPe / (usedGrowth * 100);
                    pegVal = data.current_price * (industry_peg / dynamicCompanyPeg);
                    pegMos = ((pegVal - data.current_price) / pegVal) * 100;
                } else {
                    pegVal = currentFormulaData.peg.fair_value;
                    pegMos = currentFormulaData.peg.margin_of_safety;
                }
            }
            
            const pegValueElem = document.getElementById('peg-value');
            if (pegValueElem) pegValueElem.textContent = pegVal != null ? formatCurrency(pegVal) : 'N/A';
            
            const pegStatusElem = document.getElementById('peg-status');
            const pegCompareElem = document.getElementById('peg-compare');
            
            if (pegStatusElem && pegCompareElem) {
                const currentPeg = currentFormulaData.peg ? currentFormulaData.peg.current_peg : null;
                const industryPeg = currentFormulaData.peg ? currentFormulaData.peg.industry_peg : null;

                if (currentPeg != null && industryPeg != null) {
                    const sectorPegDisplay = industryPeg.toFixed(2);
                    pegCompareElem.textContent = `PEG = ${currentPeg.toFixed(2)} vs PEG Sector = ${sectorPegDisplay}`;
                    
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
                    pegCompareElem.textContent = industryPeg == null ? "Sector data unavailable" : "PEG = N/A vs PEG Sector = N/A";
                }
            }

            // Forward Multiple Logic
            let lynchVal = null;
            let currentFwdPe = "--";
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

                let selectedMult = 20; // default
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

                // Update the FWD PE display based on chosen EPS
                if (data.current_price && targetEps > 0) {
                }
            }

            setValuationStatus(lynchVal, data.current_price, 'lynch-status', 'lynch-fair-value');

            // Relative Valuation
            let relVal = null;
            const rel = currentFormulaData.relative;
            if (rel) {
                const fvMedian = (rel.median_peer_pe != null && rel.company_eps != null) ? rel.median_peer_pe * rel.company_eps : null;
                const fvMean = (rel.mean_peer_pe != null && rel.company_eps != null) ? rel.mean_peer_pe * rel.company_eps : null;
                const fvSP500 = (rel.market_pe_trailing != null && rel.company_eps != null) ? rel.market_pe_trailing * rel.company_eps : null;

                const variantEl = document.getElementById('relative-variant');
                const variant = variantEl ? variantEl.value : 'peers';

                if (variant === 'peers') {
                    relVal = fvMedian;
                } else if (variant === 'average') {
                    relVal = fvMean;
                } else if (variant === 'sp500') {
                    relVal = fvSP500;
                }

                // Update info text
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

            // 2. Recalculate Final Fair Value and MOS
            const vals = [];
            if (lynchVal != null && lynchVal > 0 && document.getElementById('toggle-peter_lynch').checked) vals.push(lynchVal);
            if (pegVal != null && pegVal > 0 && document.getElementById('toggle-peg').checked) vals.push(pegVal);
            if (relVal != null && relVal > 0 && document.getElementById('toggle-relative').checked) vals.push(relVal);
            if (dcfVal != null && dcfVal > 0 && document.getElementById('toggle-dcf').checked) vals.push(dcfVal);

            if (vals.length > 0) {
                const finalFv = vals.reduce((a, b) => a + b, 0) / vals.length;
                elements.fairValue.textContent = formatCurrency(finalFv);

                const mos = ((finalFv - data.current_price) / finalFv) * 100;
                elements.marginSafety.textContent = `${formatPercent(mos)} Margin of Safety`;
                if (mos > 0) {
                    elements.marginSafety.style.color = 'var(--accent)';
                    elements.marginSafety.style.background = 'rgba(16, 185, 129, 0.2)';
                } else {
                    elements.marginSafety.style.color = 'var(--danger)';
                    elements.marginSafety.style.background = 'rgba(239, 68, 68, 0.2)';
                }
                updateInsightsAndScores(mos);
            } else {
                elements.fairValue.textContent = "N/A";
                elements.marginSafety.textContent = "N/A";
                elements.marginSafety.style.color = 'var(--text-muted)';
                elements.marginSafety.style.background = 'none';
                updateInsightsAndScores(null);
            }
        };

        // Custom Estimations Bindings
        const inputSelectors = [
            'fcf-source', 'dcf-custom-growth', 'dcf-custom-wacc', 'dcf-custom-perp',
            'dcf-buyback-source', 'dcf-custom-buyback',
            'relative-variant',
            'lynch-multiple', 'lynch-custom-mult', 'lynch-eps-source', 'lynch-custom-growth',
            'peg-eps-source', 'peg-custom-growth'
        ];

        inputSelectors.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                // use 'input' for text fields to update instantly as typing, 
                // and 'change' for selects
                if (el.tagName === 'SELECT') {
                    el.onchange = updateFairValue;
                } else {
                    el.oninput = updateFairValue;
                }
            }
        });

        // Trigger the recalculation to populate the initial state
        updateFairValue();

        // Listen for toggle changes
        document.querySelectorAll('.valuation-toggle').forEach(toggle => {
            // Use onchange to automatically replace any old function closures
            toggle.onchange = updateFairValue;
        });

        // Render Company Profile
        const pBody = document.getElementById('profile-body');
        if (pBody && data.company_profile) {
            const prof = data.company_profile;

            const formatBigNumber = (num, pfx = '') => {
                if (num == null) return 'N/A';
                if (num >= 1e12) return pfx + (num / 1e12).toFixed(2) + 'T';
                if (num >= 1e9) return pfx + (num / 1e9).toFixed(2) + 'B';
                if (num >= 1e6) return pfx + (num / 1e6).toFixed(2) + 'M';
                return pfx + num.toLocaleString();
            };

            pBody.innerHTML = `
                <tr><td style="padding: 12px 0; color: var(--text-muted); vertical-align: top;">Industry</td><td style="text-align: right; font-weight: bold; color: white; max-width: 220px; word-wrap: break-word;">${prof.industry}<br><span style="font-size: 0.85em; font-weight: normal; color: var(--text-muted);">${prof.sector}</span></td></tr>
                <tr style="border-top: 1px solid rgba(255,255,255,0.08);"><td style="padding: 12px 0; color: var(--text-muted); vertical-align: top;">Market Cap</td><td style="text-align: right; font-weight: bold; color: white;">${formatBigNumber(prof.market_cap, '$')}</td></tr>
                <tr style="border-top: 1px solid rgba(255,255,255,0.08);"><td style="padding: 12px 0; color: var(--text-muted); vertical-align: top;">P/E (Trailing)</td><td style="text-align: right; font-weight: bold; color: white;">${prof.trailing_pe ? prof.trailing_pe.toFixed(2) + 'x' : 'N/A'}</td></tr>
                <tr style="border-top: 1px solid rgba(255,255,255,0.08);"><td style="padding: 12px 0; color: var(--text-muted); vertical-align: top;">EPS (Trailing)</td><td style="text-align: right; font-weight: bold; color: white;">${prof.trailing_eps ? '$' + prof.trailing_eps.toFixed(2) : 'N/A'}</td></tr>
                <tr style="border-top: 1px solid rgba(255,255,255,0.08);"><td style="padding: 12px 0; color: var(--text-muted); vertical-align: top;">Debt-to-Equity</td><td style="text-align: right; font-weight: bold; color: white;">${prof.debt_to_equity != null ? prof.debt_to_equity.toFixed(2) + 'x' : 'N/A'}</td></tr>
                <tr style="border-top: 1px solid rgba(255,255,255,0.08);"><td style="padding: 12px 0; color: var(--text-muted); vertical-align: top;">Shares Out.</td><td style="text-align: right; font-weight: bold; color: white;">${formatBigNumber(prof.shares_outstanding, '')}</td></tr>
                <tr style="border-top: 1px solid rgba(255,255,255,0.08);"><td style="padding: 12px 0; color: var(--text-muted); vertical-align: top;">Buyback rate</td><td style="text-align: right; font-weight: bold; color: white;">${prof.buyback_rate != null ? (prof.buyback_rate > 0 ? '+' : '') + prof.buyback_rate.toFixed(2) + '%' : 'N/A'}</td></tr>
                <tr style="border-top: 1px solid rgba(255,255,255,0.08);"><td style="padding: 12px 0; color: var(--text-muted); vertical-align: top;">Dividend Yield</td><td style="text-align: right; font-weight: bold; color: white;">${prof.dividend_yield ? prof.dividend_yield.toFixed(2) + '%' : 'N/A'}</td></tr>
                <tr style="border-top: 1px solid rgba(255,255,255,0.08);"><td style="padding: 12px 0; color: var(--text-muted); vertical-align: top; white-space: nowrap;">Competitors</td><td style="text-align: right; font-weight: bold; color: white; word-wrap: break-word;">${prof.competitors && prof.competitors.length ? prof.competitors.join(', ') : 'None'}</td></tr>
            `;
        }

        // Render Historical Trends
        const trendsBody = document.getElementById('trends-body');
        if (trendsBody) {
            if (data.historical_trends && data.historical_trends.length > 0) {
                let html = '';
                data.historical_trends.forEach(row => {
                    // Skip rows that are essentially empty (years with no metrics)
                    if (row.revenue == null && row.net_margin == null && row.fcf == null) return;
                    
                    const revStr = row.revenue != null ? (row.revenue / 1e9).toFixed(2) : '-';
                    const marginStr = row.net_margin != null ? (row.net_margin * 100).toFixed(1) + '%' : '-';
                    const fcfStr = row.fcf != null ? (row.fcf / 1e9).toFixed(2) : '-';
                    html += `<tr>
                        <td>${row.year}</td>
                        <td>${revStr}</td>
                        <td>${marginStr}</td>
                        <td>${fcfStr}</td>
                    </tr>`;
                });
                trendsBody.innerHTML = html;
            } else {
                trendsBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 1rem;">No historical trends available.</td></tr>';
            }
        }

        loadingState.style.display = 'none';
        watchlistView.style.display = 'none'; // Ensure watchlist is hidden when showing dashboard
        dashboard.style.display = 'block';

        // Fetch and show Analyst Estimates inline
        renderAnalystEstimatesInline(data.ticker);

        // Render Historical Stability Charts
        renderHistoricalCharts(data);
    };

    // --- Watchlist Logic ---
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
        } else {
            watchlist.push(currentTicker);
        }

        saveWatchlist();
        updateWatchlistButtonState();
    };

    // --- Drag & Drop State ---
    let dragSrcIndex = null;
    let manualOrder = false; // set true after a drag so sort is skipped

    // --- Analyst Estimates Logic ---
    const analystCard = document.getElementById('analyst-estimates-card');

    const renderAnalystEstimatesInline = async (ticker) => {
        if (!ticker || !analystCard) return;

        analystCard.style.display = 'block';
        // Clear previous data
        document.getElementById('pt-avg').textContent = '...';
        document.getElementById('rec-status').textContent = '...';
        document.querySelector('#eps-est-table tbody').innerHTML = '';
        document.querySelector('#rev-est-table tbody').innerHTML = '';

        try {
            const res = await fetch(`/api/analyst/${ticker}`);
            if (!res.ok) throw new Error('API Error');
            const data = await res.json();

            if (data.error) throw new Error(data.error);

            // Price Targets
            const pt = data.price_target || {};
            document.getElementById('pt-avg').textContent = pt.avg ? `$${pt.avg.toFixed(2)}` : '--';
            document.getElementById('pt-upside').textContent = pt.upside_pct ? `${pt.upside_pct > 0 ? '+' : ''}${pt.upside_pct.toFixed(1)}%` : '--';
            document.getElementById('pt-upside').style.color = (pt.upside_pct > 0) ? 'var(--accent)' : (pt.upside_pct < 0 ? 'var(--danger)' : 'var(--text-muted)');
            document.getElementById('pt-low').textContent = pt.low ? `$${pt.low.toFixed(2)}` : '--';
            document.getElementById('pt-high').textContent = pt.high ? `$${pt.high.toFixed(2)}` : '--';

            // Recommendation
            const rec = data.recommendation || {};
            const statusElem = document.getElementById('rec-status');
            
            // Rec Bars & Determine Max Category
            const counts = rec.counts || {};
            const maxVal = Math.max(...Object.values(counts), 1);
            const barsContainer = document.getElementById('rec-bars');
            barsContainer.innerHTML = '';

            const labels = { strongBuy: 'S. Buy', buy: 'Buy', hold: 'Hold', sell: 'Sell', strongSell: 'S. Sell' };
            const fullLabels = { strongBuy: 'STRONG BUY', buy: 'BUY', hold: 'HOLD', sell: 'SELL', strongSell: 'STRONG SELL' };
            
            let topCategory = 'N/A';
            let topCount = -1;

            ['strongBuy', 'buy', 'hold', 'sell', 'strongSell'].forEach(k => {
                const count = counts[k] || 0;
                if (count > topCount) {
                    topCount = count;
                    topCategory = fullLabels[k];
                }
                const pct = (count / maxVal) * 100;
                barsContainer.innerHTML += `
                    <div class="rec-bar-row">
                        <span class="rec-bar-label">${labels[k]}</span>
                        <div class="rec-bar-bg"><div class="rec-bar-fill" style="width: ${pct}%;"></div></div>
                        <span class="rec-bar-count">${count}</span>
                    </div>
                `;
            });
            
            // Set logic: display the true category with the most votes, unless none exist
            statusElem.textContent = topCount > 0 ? topCategory : ((rec.key || 'N/A').replace('_', ' ').toUpperCase());
            document.getElementById('rec-mean').textContent = `Score: ${rec.mean ? rec.mean.toFixed(2) : '--'} (1-5)`;

            // Tables Shared Helpers
            const fvScale = (v) => v != null ? `$${v.toFixed(2)}` : '--';
            const fvPct = (v) => v != null ? `${(v * 100).toFixed(1)}%` : '--';
            const fvM = (v) => {
                if (v == null) return '--';
                return (v / 1e9).toFixed(2); // In Billions
            };

            // EPS Table
            const epsBody = document.querySelector('#eps-est-table tbody');
            (data.eps_estimates || []).slice(0, 8).forEach(row => {
                let colorKey = 'var(--text-main)';
                let finalVal = fvPct(row.growth); // Use growth default

                if (row.status === 'reported') {
                    // It's a reported quarter, use surprise if possible
                    colorKey = (row.surprise_pct > 0) ? 'var(--accent)' : (row.surprise_pct < 0 ? 'var(--danger)' : 'var(--text-main)');
                    finalVal = (row.surprise_pct != null) ? fvPct(row.surprise_pct) : '--';
                }

                epsBody.innerHTML += `<tr>
                    <td style="padding: 0.4rem 0;">${row.period}</td>
                    <td style="text-align: right; font-weight: 600;">${fvScale(row.avg)}</td>
                    <td style="text-align: right; color: ${colorKey};">${finalVal}</td>
                </tr>`;
            });

            // Revenue Table
            const revBody = document.querySelector('#rev-est-table tbody');
            (data.rev_estimates || []).slice(0, 8).forEach(row => {
                let colorKey = 'var(--text-main)';
                let finalVal = fvPct(row.growth);

                if (row.status === 'reported') {
                    // Usually no clean surprise % for revenue available, so neutral unless set
                    finalVal = (row.surprise_pct != null) ? fvPct(row.surprise_pct) : '--';
                    if (row.surprise_pct > 0) colorKey = 'var(--accent)';
                    else if (row.surprise_pct < 0) colorKey = 'var(--danger)';
                }

                revBody.innerHTML += `<tr>
                    <td style="padding: 0.4rem 0;">${row.period}</td>
                    <td style="text-align: right; font-weight: 600;">${fvM(row.avg)}</td>
                    <td style="text-align: right; color: ${colorKey};">${finalVal}</td>
                </tr>`;
            });

        } catch (err) {
            console.error("Analyst inline error:", err);
            analystCard.style.display = 'none';
        }
    };

    // Mobile Tab Switching Logic
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            // Update Buttons
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            // Update Contents
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(`tab-${targetTab}`).classList.add('active');
        });
    });

    const renderAnalystEstimates = async () => {
        // Obsolete separate view logic - just trigger inline instead or stay here
        if (currentTicker) renderAnalystEstimatesInline(currentTicker);
    };
    const renderWatchlistUI = () => {
        watchlistGrid.innerHTML = '';
        const watchlistHeader = document.getElementById('watchlist-header');

        if (!cachedWatchlistData || cachedWatchlistData.length === 0) {
            emptyWatchlistMsg.style.display = 'block';
            if (watchlistHeader) watchlistHeader.style.display = 'none';
            return;
        }

        emptyWatchlistMsg.style.display = 'none';

        // Only sort if user hasn't manually reordered
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
            const card = document.createElement('div');
            card.className = 'glass-card watchlist-card';
            card.setAttribute('draggable', 'true');
            card.onclick = (e) => {
                if (e.target.closest('.drag-handle')) return;
                card.classList.toggle('expanded');
            };

            // Format Margin of Safety Color
            let mosColor = 'var(--text-main)';
            let mosText = 'N/A';
            if (data.margin_of_safety != null) {
                mosText = formatPercent(data.margin_of_safety);
                mosColor = data.margin_of_safety > 0 ? 'var(--accent)' : 'var(--danger)';
                if (data.margin_of_safety > 0 && !mosText.startsWith('+')) {
                    mosText = '+' + mosText;
                }
            }

            const dcfVal = data.dcf_value != null ? formatCurrency(data.dcf_value) : 'N/A';
            const relVal = data.relative_value != null ? formatCurrency(data.relative_value) : 'N/A';
            const pegVal = data.peg_value != null ? formatCurrency(data.peg_value) : 'N/A';

            let fwdMultVal = 'N/A';
            if (data.lynch_fair_value != null) {
                fwdMultVal = formatCurrency(data.lynch_fair_value);
            } else if (data.peter_lynch && data.peter_lynch.fair_value_pe_20) {
                fwdMultVal = formatCurrency(data.peter_lynch.fair_value_pe_20);
            }

            // Scoring logic
            const hs = data.health_score;
            const bs = data.buy_score;
            const hsN = (hs !== 'N/A' && hs != null) ? hs : null;
            const bsN = (bs !== 'N/A' && bs != null) ? bs : null;

            const hsColorClass = hsN >= 76 ? 'bg-score-green' : (hsN >= 41 ? 'bg-score-yellow' : 'bg-score-red');
            const bsColorClass = bsN >= 76 ? 'bg-score-green' : (bsN >= 41 ? 'bg-score-yellow' : 'bg-score-red');
            const hsTextClass = hsN >= 76 ? 'score-green' : (hsN >= 41 ? 'score-yellow' : 'score-red');
            const bsTextClass = bsN >= 76 ? 'score-green' : (bsN >= 41 ? 'score-yellow' : 'score-red');
            const hsFlex = hsN != null ? `${hsN}%` : '0%';
            const bsFlex = bsN != null ? `${bsN}%` : '0%';

            card.innerHTML = `
                <div class="watchlist-row">
                    <div class="drag-handle" title="Drag to reorder">⠿</div>
                    <div class="watchlist-left">
                        <span class="expand-icon">▼</span>
                        <div class="watchlist-ticker-info">
                            <span class="watchlist-ticker">${data.ticker}</span>
                            <span class="watchlist-name" title="${data.name}">${data.name}</span>
                        </div>
                    </div>
                    <div class="watchlist-metrics">
                        <div class="watchlist-mobile-col-header">
                            <span>PRICE</span>
                            <span>FAIR VALUE</span>
                            <span>MOS</span>
                        </div>
                        <div class="watchlist-metric col-price">
                            <span class="value">${data.current_price != null ? formatCurrency(data.current_price) : 'N/A'}</span>
                        </div>
                        <div class="watchlist-metric col-fv">
                            <span class="value">${data.fair_value != null ? formatCurrency(data.fair_value) : 'N/A'}</span>
                        </div>
                        <div class="watchlist-metric col-mos">
                            <span class="value" style="color: ${mosColor}; font-weight: 700;">${mosText}</span>
                        </div>
                    </div>
                    
                    <div class="watchlist-scores-container">
                        <div class="watchlist-score-item">
                            <span class="score-label">Health:</span>
                            <div class="mini-score-bar">
                                <div class="mini-score-fill ${hsN != null ? hsColorClass : ''}" style="width: ${hsFlex};"></div>
                            </div>
                            <span class="score-val ${hsN != null ? hsTextClass : ''}">${hsN != null ? hsN : 'N/A'}/100</span>
                        </div>
                        <div class="watchlist-score-item">
                            <span class="score-label">Buy Score:</span>
                            <div class="mini-score-bar">
                                <div class="mini-score-fill ${bsN != null ? bsColorClass : ''}" style="width: ${bsFlex};"></div>
                            </div>
                            <span class="score-val ${bsN != null ? bsTextClass : ''}">${bsN != null ? bsN : 'N/A'}/100</span>
                        </div>
                    </div>

                    <div class="watchlist-actions">
                        <button class="remove-watchlist-btn" data-ticker="${data.ticker}" title="Remove from Watchlist">✖</button>
                    </div>
                </div>
                
                <div class="watchlist-expanded" onclick="event.stopPropagation();">
                    <div class="breakdown-title">Valuation Breakdown (Equal-Weighted)</div>
                    <div class="breakdown-grid">
                        <div class="breakdown-item">
                            <span class="breakdown-label">DCF Model:</span>
                            <span class="breakdown-value">${dcfVal}</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="breakdown-label">Forward Multiple:</span>
                            <span class="breakdown-value">${fwdMultVal}</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="breakdown-label">Relative Valuation:</span>
                            <span class="breakdown-value">${relVal}</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="breakdown-label">PEG Target (1.0):</span>
                            <span class="breakdown-value">${pegVal}</span>
                        </div>
                    </div>
                    <div class="view-analysis-row">
                        <button class="view-analysis-btn" data-ticker="${data.ticker}">[ View Full Analysis → ]</button>
                    </div>
                </div>
            `;

            // --- Drag & Drop Events ---
            card.addEventListener('dragstart', (e) => {
                dragSrcIndex = index;
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', String(index));
                // Delay adding class so screenshot isn't blank
                setTimeout(() => card.classList.add('dragging'), 0);
            });

            card.addEventListener('dragend', () => {
                card.classList.remove('dragging');
                document.querySelectorAll('.watchlist-card').forEach(c => {
                    c.classList.remove('drag-over-top', 'drag-over-bottom');
                });
            });

            card.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                if (dragSrcIndex === null || dragSrcIndex === index) return;
                // Clear all first
                document.querySelectorAll('.watchlist-card').forEach(c => {
                    c.classList.remove('drag-over-top', 'drag-over-bottom');
                });
                const rect = card.getBoundingClientRect();
                if (e.clientY < rect.top + rect.height / 2) {
                    card.classList.add('drag-over-top');
                } else {
                    card.classList.add('drag-over-bottom');
                }
            });

            card.addEventListener('dragleave', (e) => {
                // Only remove if we really left this card (not just entering a child)
                if (!card.contains(e.relatedTarget)) {
                    card.classList.remove('drag-over-top', 'drag-over-bottom');
                }
            });

            card.addEventListener('drop', (e) => {
                e.preventDefault();
                e.stopPropagation();
                card.classList.remove('drag-over-top', 'drag-over-bottom');

                const from = dragSrcIndex;
                if (from === null || from === index) { dragSrcIndex = null; return; }

                const rect = card.getBoundingClientRect();
                let to = (e.clientY >= rect.top + rect.height / 2) ? index + 1 : index;

                // Operate on the currently displayed sorted array
                const reordered = [...sortedResults];
                const [moved] = reordered.splice(from, 1);
                const insertAt = from < to ? to - 1 : to;
                reordered.splice(insertAt, 0, moved);

                // Write back to the shared cache and watchlist
                cachedWatchlistData = reordered;
                watchlist = cachedWatchlistData.map(d => d.ticker);
                manualOrder = true;
                dragSrcIndex = null;

                saveWatchlist();
                renderWatchlistUI();
            });

            watchlistGrid.appendChild(card);
        });

        // Add remove event listeners
        document.querySelectorAll('.remove-watchlist-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation(); // prevent triggering the card click (expand/collapse)
                const tickerToRemove = e.target.getAttribute('data-ticker');
                watchlist = watchlist.filter(t => t !== tickerToRemove);

                if (cachedWatchlistData) {
                    cachedWatchlistData = cachedWatchlistData.filter(d => d.ticker !== tickerToRemove);
                }

                saveWatchlist();
                if (currentTicker === tickerToRemove) {
                    updateWatchlistButtonState();
                }
                renderWatchlistUI(); // Re-render from cache instantly
            });
        });

        // Add view full analysis event listeners
        document.querySelectorAll('.view-analysis-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const targetTicker = e.target.getAttribute('data-ticker');
                tickerInput.value = targetTicker;

                // Switch to dashboard view
                watchlistView.style.display = 'none';

                analyzeTicker();
            });
        });
    };

    const renderWatchlist = async () => {
        // UI Transition
        dashboard.style.display = 'none';
        loadingState.style.display = 'flex';
        watchlistView.style.display = 'none';
        watchlistGrid.innerHTML = '';

        const watchlistHeader = document.getElementById('watchlist-header');

        if (watchlist.length === 0) {
            loadingState.style.display = 'none';
            watchlistView.style.display = 'block';
            emptyWatchlistMsg.style.display = 'block';
            if (watchlistHeader) watchlistHeader.style.display = 'none';
            cachedWatchlistData = [];
            return;
        }

        emptyWatchlistMsg.style.display = 'none';

        // Fetch data for all watchlist items
        try {
            const promises = watchlist.map(ticker =>
                fetch(`/api/valuation/${encodeURIComponent(ticker)}`).then(res => res.json())
            );

            let results = await Promise.all(promises);
            cachedWatchlistData = results.filter(data => !data.detail); // Skip raw errors

            renderWatchlistUI();

        } catch (error) {
            console.error('Error fetching watchlist data:', error);
            watchlistGrid.innerHTML = '<p style="color: var(--danger); grid-column: 1/-1;">Error loading watchlist data. Please try again.</p>';
        }

        loadingState.style.display = 'none';
        watchlistView.style.display = 'block';
    };
    // --- Watchlist Sort Logic ---
    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const sortKey = btn.getAttribute('data-sort');

            if (currentSort.column === sortKey) {
                // Toggle order
                currentSort.order = currentSort.order === 'desc' ? 'asc' : 'desc';
            } else {
                // New column, default to desc for MOS/Price, asc for Ticker
                currentSort.column = sortKey;
                currentSort.order = sortKey === 'ticker' ? 'asc' : 'desc';
            }

            // Update UI 
            document.querySelectorAll('.sort-btn').forEach(b => {
                b.classList.remove('active-sort', 'desc', 'asc');
                const tKey = b.getAttribute('data-sort');
                if (tKey === 'mos') b.style.color = 'var(--text-muted)'; // reset color
                b.querySelector('.sort-icon').textContent = '↕';
            });

            btn.classList.add('active-sort');
            btn.classList.add(currentSort.order);
            btn.querySelector('.sort-icon').textContent = currentSort.order === 'desc' ? '▼' : '▲';

            // Reapply special color for active MOS sort
            if (sortKey === 'mos') {
                btn.style.color = 'var(--accent)';
            }

            if (cachedWatchlistData) {
                manualOrder = false; // re-enable sort when user explicitly clicks a sort button
                renderWatchlistUI();
            }
        });
    });

    // --- Search Autocomplete Logic ---
    let searchTimeout = null;

    tickerInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(searchTimeout);

        if (query.length < 1) {
            autocompleteList.style.display = 'none';
            return;
        }

        searchTimeout = setTimeout(async () => {
            try {
                const res = await fetch(`/api/search/${encodeURIComponent(query)}`);
                const data = await res.json();

                autocompleteList.innerHTML = '';

                if (data.length > 0) {
                    data.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'autocomplete-item';
                        div.innerHTML = `<strong>${item.ticker}</strong> <span>${item.name}</span>`;
                        div.onclick = () => {
                            tickerInput.value = item.ticker;
                            autocompleteList.style.display = 'none';
                            analyzeTicker(item.ticker);
                        };
                        autocompleteList.appendChild(div);
                    });
                    autocompleteList.style.display = 'block';
                } else {
                    autocompleteList.style.display = 'none';
                }
            } catch (err) {
                console.error("Autocomplete error:", err);
            }
        }, 300); // 300ms debounce
    });

    // Close autocomplete on click outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.autocomplete-wrapper')) {
            autocompleteList.style.display = 'none';
        }
    });

    // --- Score Breakdown Modals ---
    const scoreModal = document.getElementById('score-modal');
    const closeScoreModal = document.getElementById('close-score-modal');
    const scoreModalTitle = document.getElementById('score-modal-title');
    const scoreModalPts = document.getElementById('score-modal-pts');
    const scoreModalBodyContent = document.getElementById('score-modal-body-content');

    const renderScoreModal = (title, totalScore, breakdownData) => {
        scoreModalTitle.textContent = title;
        scoreModalPts.textContent = totalScore;

        let html = '';
        if (breakdownData && breakdownData.length > 0) {
            breakdownData.forEach(item => {
                // Determine color based on points vs max points
                let colorClass = 'score-yellow'; // default yellow
                let badgeClass = 'bg-score-yellow';

                if (item.points === item.max_points) {
                    colorClass = 'score-green';
                    badgeClass = 'bg-score-green';
                } else if (item.points === 0 || item.points <= (item.max_points / 3)) {
                    // Logic handles 'null' NA items which usually have 0 points, or mathematically lowest tier
                    colorClass = 'score-red';
                    badgeClass = 'bg-score-red';
                }

                html += `
                    <div class="score-breakdown-row">
                        <div class="score-row-name">${item.name}</div>
                        <div class="score-row-val">${item.value !== null ? item.value : 'N/A'}</div>
                        <div class="score-row-pts ${colorClass}">
                            <span class="score-badge ${badgeClass}"></span>
                            ${item.points}/${item.max_points} pts
                        </div>
                    </div>
                `;
            });
        } else {
            html = '<p>No breakdown data available.</p>';
        }

        scoreModalBodyContent.innerHTML = html;
        scoreModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    };

    // Attach click events to the score rows
    const healthScoreRow = document.querySelector('.score-row:has(#health-score-circle)');
    const buyScoreRow = document.querySelector('.score-row:has(#buy-score-circle)');

    if (healthScoreRow) {
        healthScoreRow.style.cursor = 'pointer';
        healthScoreRow.addEventListener('click', () => {
            if (currentHealthBreakdown) {
                renderScoreModal('Company Health Breakdown', document.getElementById('health-score-circle').textContent, currentHealthBreakdown);
            }
        });
    }

    if (buyScoreRow) {
        buyScoreRow.style.cursor = 'pointer';
        buyScoreRow.addEventListener('click', () => {
            if (currentBuyBreakdown) {
                renderScoreModal('Good to Buy Score Breakdown', document.getElementById('buy-score-circle').textContent, currentBuyBreakdown);
            }
        });
    }

    closeScoreModal.addEventListener('click', () => {
        scoreModal.style.display = 'none';
        document.body.style.overflow = '';
    });

    window.addEventListener('click', (e) => {
        if (e.target === scoreModal) {
            scoreModal.style.display = 'none';
            document.body.style.overflow = '';
        }
    });

    // --- Event Listeners ---
    logoBtn.addEventListener('click', () => {
        if (currentTicker && currentFormulaData) {
            // If we have a ticker loaded, just switch back to dashboard view
            watchlistView.style.display = 'none';
            dashboard.style.display = 'block';
        } else {
            window.location.reload();
        }
    });

    searchBtn.addEventListener('click', () => analyzeTicker());
    tickerInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            autocompleteList.style.display = 'none';
            analyzeTicker();
        }
    });

    navWatchlistBtn.addEventListener('click', () => {
        dashboard.style.display = 'none';
        renderWatchlist();
    });

    addToWatchlistBtn.addEventListener('click', toggleWatchlist);

    // Modal Logic
    viewDataBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (!currentFormulaData) return;

            const method = e.target.getAttribute('data-method');
            const modalTitle = document.getElementById('modal-title');

            if (method === 'peter_lynch') modalTitle.textContent = "Forward Multiple Valuation";
            else if (method === 'peg') modalTitle.textContent = "PEG Target (1.0)";
            else if (method === 'relative') modalTitle.textContent = "Relative Valuation";
            else if (method === 'dcf') modalTitle.textContent = "Discounted Cash Flow";
            else modalTitle.textContent = "Formula Data Used";

            let html = '';

            const fv = (val, isPct = false) => {
                if (val == null) return "N/A";
                if (isPct) return `${(val * 100).toFixed(2)}%`;
                return typeof val === 'number' ? val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : val;
            };

            const fM = (val) => {
                if (val == null) return "N/A";
                if (Math.abs(val) >= 1e9) {
                    return `$${(val / 1e9).toFixed(2)}B`;
                } else if (Math.abs(val) >= 1e6) {
                    return `$${(val / 1e6).toFixed(2)}M`;
                }
                return `$${typeof val === 'number' ? val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : val}`;
            };

            if (method === 'peter_lynch') {
                const pl = currentFormulaData.peter_lynch;
                if (pl) {
                    html += `
                        <div class="formula-section">
                            <ul>
                                <li><strong>Current Price:</strong> <span>$${fv(pl.current_price)}</span></li>
                                <li><strong>Diluted Trailing EPS:</strong> <span>$${fv(pl.trailing_eps)}</span></li>
                                <li><strong>Est. 3-Year CAGR:</strong> <span>${fv(pl.eps_growth_estimated, true)}</span></li>
                                <li><strong>3-Year FWD EPS:</strong> <span>$${fv(pl.fwd_eps)}</span></li>
                                <li><strong>3Y FWD PE:</strong> <span>${fv(pl.fwd_pe)}x</span></li>
                                <li style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
                                    <strong>Fair Value (if PE=20):</strong> <span>$${fv(pl.fair_value_pe_20)}</span>
                                </li>
                                <li>
                                    <strong>Fair Value (PE=Sector Median):</strong> <span>$${fv(pl.fair_value_sector_pe)}</span>
                                </li>
                                <li>
                                    <strong>Fair Value (Historic PE ${fv(pl.historic_pe)}x):</strong> <span style="color:var(--accent); font-weight:bold;">$${fv(pl.fair_value)}</span>
                                </li>
                            </ul>
                        </div>
                    `;
                }
            } else if (method === 'peg') {
                const peg = currentFormulaData.peg;
                if (peg) {
                    const targetText = peg.industry_peg != null ? fv(peg.industry_peg) : 'N/A';
                    const targetLabel = peg.industry_peg != null ? 'Target PEG (Sector):' : 'Target PEG:';
                    
                    if (modalTitle) modalTitle.textContent = peg.industry_peg != null ? 'PEG Target (Sector)' : 'PEG Valuation Data';

                    html += `
                        <div class="formula-section">
                            <ul>
                                <li><strong>Current PEG:</strong> <span>${peg.current_peg != null ? fv(peg.current_peg) : 'N/A'}</span></li>
                                <li><strong>${targetLabel}</strong> <span>${targetText}</span></li>
                                <li style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
                                    <strong>Fair Value:</strong> <span style="color:var(--accent); font-weight:bold;">$${peg.fair_value != null ? fv(peg.fair_value) : 'N/A'}</span>
                                </li>
                                <li style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
                                    <strong>Margin of Safety:</strong> 
                                    <span style="color:${peg.margin_of_safety > 0 ? 'var(--accent)' : 'var(--danger)'}; font-weight:bold;">
                                        ${peg.margin_of_safety != null ? peg.margin_of_safety.toFixed(2) + '%' : 'N/A'}
                                    </span>
                                </li>
                            </ul>
                            ${peg.industry_peg == null ? '<p style="color: var(--danger); font-size: 0.9rem; margin-top: 1rem;">Sector data unavailable</p>' : ''}
                        </div>
                    `;
                }
            } else if (method === 'relative') {
                const rel = currentFormulaData.relative;
                if (rel) {
                    const fvPeers = (rel.median_peer_pe && rel.company_eps) ? (rel.median_peer_pe * rel.company_eps).toFixed(2) : null;
                    const fvSP500 = (rel.market_pe_trailing && rel.company_eps) ? (rel.market_pe_trailing * rel.company_eps).toFixed(2) : null;
                    const peersHtml = rel.peers_used && rel.peers_used.length
                        ? rel.peers_used.map(p => `<span style="display:inline-block;background:rgba(255,255,255,0.07);border-radius:4px;padding:1px 6px;margin:2px 2px;font-size:0.82em;">${p}</span>`).join('')
                        : '<span style="color:var(--text-muted)">None found</span>';

                    const row = (label, value, highlight = false) => `
                        <tr style="border-bottom:1px solid rgba(255,255,255,0.07);">
                            <td style="padding:10px 0;color:var(--text-muted);vertical-align:top;padding-right:16px;">${label}</td>
                            <td style="padding:10px 0 10px 12px;text-align:right;font-weight:${highlight ? 700 : 500};color:${highlight ? 'var(--accent)' : 'white'};word-break:break-word;">${value}</td>
                        </tr>`;

                    html += `
                        <div class="formula-section">
                            <table style="width:100%;border-collapse:collapse;">
                                ${row('Company Trailing EPS:', `$${fv(rel.company_eps)}`)}
                                ${row('Company Trailing P/E:', rel.company_trailing_pe != null ? `${fv(rel.company_trailing_pe)}x` : 'N/A')}
                                <tr style="border-bottom:1px solid rgba(255,255,255,0.07);">
                                    <td style="padding:10px 0;color:var(--text-muted);vertical-align:top;padding-right:16px;">Peers Used (Industry):</td>
                                    <td style="padding:10px 0 10px 12px;text-align:right;">${peersHtml}</td>
                                </tr>
                                ${row('Peer Group Median Trailing P/E:', rel.median_peer_pe != null ? `${fv(rel.median_peer_pe)}x` : 'N/A')}
                                <tr style="border-top:2px solid rgba(255,255,255,0.12);">
                                    <td style="padding:12px 0 6px 0;color:var(--text-muted);vertical-align:middle;padding-right:16px;">Fair Value vs. Peers:</td>
                                    <td style="padding:12px 0 6px 12px;text-align:right;font-weight:700;font-size:1.1em;color:${fvPeers ? 'var(--accent)' : 'var(--text-muted)'};">${fvPeers ? '$' + fvPeers : 'N/A'}</td>
                                </tr>
                                <tr>
                                    <td style="padding:6px 0 12px 0;color:var(--text-muted);vertical-align:middle;padding-right:16px;">Fair Value vs. S&amp;P 500:</td>
                                    <td style="padding:6px 0 12px 12px;text-align:right;font-weight:700;font-size:1.1em;color:${fvSP500 ? 'var(--accent)' : 'var(--text-muted)'};">${fvSP500 ? '$' + fvSP500 : 'N/A'}</td>
                                </tr>
                                <tr>
                                    <td colspan="2" style="padding:4px 0;font-size:0.78em;color:var(--text-muted);">
                                        S&amp;P 500 Trailing P/E used: ${rel.market_pe_trailing != null ? rel.market_pe_trailing + 'x' : 'N/A'} &nbsp;|&nbsp; Forward P/E: ${rel.market_pe_forward != null ? rel.market_pe_forward + 'x' : 'N/A'}
                                    </td>
                                </tr>
                            </table>
                        </div>
                    `;
                }
            } else if (method === 'dcf') {
                const dcf = currentFormulaData.dcf;
                if (dcf && dcf.intrinsic_value != null) {
                    let tableRows = '';
                    if (dcf.fcf_years && dcf.pv_fcf_years) {
                        dcf.fcf_years.forEach((cf, i) => {
                            let growthStr = '--';
                            if (i === 0) {
                                // Growth from base FCF
                                const baseFcf = dcf.fcf;
                                if (baseFcf && baseFcf > 0) {
                                    growthStr = `${((cf - baseFcf) / baseFcf * 100).toFixed(1)}%`;
                                }
                            } else {
                                const prevFcf = dcf.fcf_years[i-1];
                                if (prevFcf && prevFcf > 0) {
                                    growthStr = `${((cf - prevFcf) / prevFcf * 100).toFixed(1)}%`;
                                }
                            }
                            tableRows += `<tr>
                                <td style="padding: 4px 0;">Year ${i + 1}</td>
                                <td style="text-align: right;">${fM(cf)}</td>
                                <td style="text-align: right; color: var(--text-muted); font-size: 0.85em;">${growthStr}</td>
                                <td style="text-align: right;">${fM(dcf.pv_fcf_years[i])}</td>
                            </tr>`;
                        });
                    }
                    html += `
                        <div class="formula-section">
                            <ul>
                                <li><strong>Discount Rate (WACC):</strong> <span>${fv(dcf.discount_rate, true)}</span></li>
                                <li><strong>Perpetual Growth Rate:</strong> <span>${fv(dcf.perpetual_growth, true)}</span></li>
                                <li><strong>Shares Outstanding:</strong> <span>${fM(dcf.shares_outstanding).replace('$', '')}</span></li>
                            </ul>
                            <div class="table-responsive">
                                <table style="width:100%; min-width: 400px; text-align:left; margin-top: 1rem; margin-bottom: 1rem; border-collapse: collapse; font-size: 0.9rem;">
                                    <thead>
                                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                                            <th style="padding-bottom: 5px;">Year</th>
                                            <th style="padding-bottom: 5px; text-align: right;">Projected FCF</th>
                                            <th style="padding-bottom: 5px; text-align: right;">Growth (YoY)</th>
                                            <th style="padding-bottom: 5px; text-align: right;">Present Value</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${tableRows}
                                    </tbody>
                                </table>
                            </div>
                            <ul>
                                <li><strong>Total PV of FCFs:</strong> <span>${fM(dcf.sum_pv_cf)}</span></li>
                                <li><strong>Terminal Value:</strong> <span>${fM(dcf.terminal_value)}</span></li>
                                <li><strong>PV of Terminal Value:</strong> <span>${fM(dcf.pv_terminal_value)}</span></li>
                                <li style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
                                    <strong>Enterprise Value:</strong> <span style="font-weight:bold;">${fM(dcf.enterprise_value)}</span>
                                </li>
                                <li style="color: var(--accent);"><strong>+ Cash & Equivalents:</strong> <span>${fM(dcf.total_cash)}</span></li>
                                <li style="color: var(--danger);"><strong>- Total Debt:</strong> <span>${fM(dcf.total_debt)}</span></li>
                                <li style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
                                    <strong>Equity Value:</strong> <span style="font-weight:bold;">${fM(dcf.equity_value)}</span>
                                </li>
                                <li style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
                                    <strong>Intrinsic Value per Share:</strong> 
                                    <span style="color:var(--accent); font-weight:bold;">$${fv(dcf.intrinsic_value)}</span>
                                </li>
                                <li style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
                                    <strong>Market Implied FCF Growth (Reverse DCF):</strong> 
                                    <span style="color:var(--accent); font-weight:bold;">${dcf.reverse_dcf_growth != null ? (dcf.reverse_dcf_growth * 100).toFixed(2) + '%' : 'N/A'}</span>
                                </li>
                            </ul>
                            
                            ${dcf.sensitivity_matrix && dcf.sensitivity_matrix.length > 0 ? `
                                <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem; color: var(--text-main);">DCF Sensitivity Matrix</h4>
                                <div class="table-responsive">
                                    <table class="sensitivity-matrix" style="min-width: 450px;">
                                        <thead>
                                            <tr>
                                                <th style="font-size: 0.8em; color: var(--text-muted); text-align: left;">WACC \\ g</th>
                                                ${dcf.sensitivity_matrix[0].values.map(v => `<th>${(v.perpetual_growth * 100).toFixed(1)}%</th>`).join('')}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${dcf.sensitivity_matrix.map(row => `
                                                <tr>
                                                    <th>${(row.discount_rate * 100).toFixed(1)}%</th>
                                                    ${row.values.map(v => {
                        let fvVal = v.fair_value;
                        return `<td>${fvVal != null ? '$' + fvVal.toFixed(2) : 'N/A'}</td>`;
                    }).join('')}
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            ` : ''}
                        </div>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="formula-section">
                            <p>Discounted Cash Flow (DCF) model is not applicable for this company. This usually occurs when the company has negative or missing Free Cash Flow.</p>
                        </div>
                    `;
                }
            }

            modalBodyContent.innerHTML = html || '<p>No data available</p>';
            dataModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        });
    });

    closeModal.addEventListener('click', () => {
        dataModal.style.display = 'none';
        document.body.style.overflow = '';
    });

    window.addEventListener('click', (e) => {
        if (e.target === dataModal) {
            dataModal.style.display = 'none';
            document.body.style.overflow = '';
        }
    });

    // Initialize View
    // Custom Estimations Logic (in-card)
    const specs = [
        { sel: 'dcf-custom-select', grp: 'dcf-custom-input-group', inp: 'dcf-custom-fcf-growth' },
        { sel: 'lynch-custom-select', grp: 'lynch-custom-input-group', inp: 'lynch-custom-eps-growth' },
        { sel: 'peg-custom-select', grp: 'peg-custom-input-group', inp: 'peg-custom-eps-growth' }
    ];

    specs.forEach(s => {
        const selEl = document.getElementById(s.sel);
        const grpEl = document.getElementById(s.grp);
        const inpEl = document.getElementById(s.inp);
        if (selEl && grpEl && inpEl) {
            selEl.addEventListener('change', (e) => {
                grpEl.style.display = e.target.value === 'custom' ? 'flex' : 'none';
                // Trigger global generic listener that updates fair value if a ticker is loaded
                if (currentFormulaData) {
                    const btn = document.createElement('button');
                    btn.className = 'custom-trigger-temp';
                    btn.style.display = 'none';
                    document.body.appendChild(btn);
                    btn.onclick = () => { if (typeof updateFairValue !== 'undefined') { /* This works inside renderDashboard */ } };
                    // Because Javascript scope: updateFairValue is inside renderDashboard.
                    // Oh wait! updateFairValue is defined inside renderDashboard, so it's not accessible here!
                    // Let's rely on the user changing the input to trigger it, OR we simply dispatch an event 
                    // that renderDashboard listens to? 
                    // The easiest fix is to attach these listeners INSIDE renderDashboard or just dispatch an event.
                }
            });
        }
    });
    fetch('/api/watchlist')
        .then(res => res.json())
        .then(data => {
            if (Array.isArray(data) && data.length > 0) {
                watchlist = data;
                localStorage.setItem('fairValueWatchlist', JSON.stringify(watchlist));
                renderWatchlist();
            } else if (watchlist.length > 0) {
                renderWatchlist(); // Fallback to localStorage if API is empty but local is not (e.g., first sync)
            } else {
                watchlistView.style.display = 'block';
                emptyWatchlistMsg.style.display = 'block';
            }
        })
        .catch(err => {
            console.error('Failed to load watchlist from server:', err);
            if (watchlist.length > 0) {
                renderWatchlist();
            } else {
                watchlistView.style.display = 'block';
                emptyWatchlistMsg.style.display = 'block';
            }
        });
    const renderHistoricalCharts = (data) => {
        const container = document.getElementById('historical-charts-container');
        if (!data.historical_data || !data.historical_data.years || data.historical_data.years.length === 0) {
            if (container) container.style.display = 'none';
            return;
        }

        if (container) container.style.display = 'block';
        const h = data.historical_data;

        // Helper to format large numbers to Millions
        const toM = (val) => (val / 1000000);

        // Chart 1: Revenue & FCF (Bar Chart)
        if (chartRevFcf) chartRevFcf.destroy();
        const ctx1 = document.getElementById('chart-rev-fcf').getContext('2d');
        chartRevFcf = new Chart(ctx1, {
            type: 'bar',
            data: {
                labels: h.years,
                datasets: [
                    {
                        label: 'Revenue (M)',
                        data: h.revenue.map(toM),
                        backgroundColor: 'rgba(56, 189, 248, 0.6)',
                        borderColor: 'rgba(56, 189, 248, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Free Cash Flow (M)',
                        data: h.fcf.map(toM),
                        backgroundColor: 'rgba(34, 197, 94, 0.6)',
                        borderColor: 'rgba(34, 197, 94, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        ticks: { color: 'rgba(255,255,255,0.6)' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: 'rgba(255,255,255,0.6)' }
                    }
                },
                plugins: {
                    legend: { labels: { color: 'rgba(255,255,255,0.8)' } }
                }
            }
        });

        // Chart 2: EPS & Shares Outstanding (Dual Y Axis)
        if (chartEpsShares) chartEpsShares.destroy();
        const ctx2 = document.getElementById('chart-eps-shares').getContext('2d');
        chartEpsShares = new Chart(ctx2, {
            type: 'line',
            data: {
                labels: h.years,
                datasets: [
                    {
                        label: 'EPS',
                        data: h.eps,
                        borderColor: 'rgba(234, 179, 8, 1)',
                        backgroundColor: 'rgba(234, 179, 8, 0.2)',
                        yAxisID: 'y',
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: 'Shares (M)',
                        data: h.shares.map(toM),
                        borderColor: 'rgba(168, 85, 247, 1)',
                        backgroundColor: 'rgba(168, 85, 247, 0.2)',
                        yAxisID: 'y1',
                        borderDash: [5, 5],
                        type: 'bar'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'EPS ($)', color: 'rgba(234, 179, 8, 1)' },
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        ticks: { color: 'rgba(255,255,255,0.6)' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Shares (Millions)', color: 'rgba(168, 85, 247, 1)' },
                        grid: { drawOnChartArea: false },
                        ticks: { color: 'rgba(255,255,255,0.6)' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: 'rgba(255,255,255,0.6)' }
                    }
                },
                plugins: {
                    legend: { labels: { color: 'rgba(255,255,255,0.8)' } }
                }
            }
        });
    };
});

