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

    let watchlist = JSON.parse(localStorage.getItem('fairValueWatchlist')) || [];

    // --- STICKY BANNER LOGIC ---
    const stickyBanner = document.getElementById('sticky-top-banner');
    window.addEventListener('scroll', () => {
        if (!stickyBanner) return;
        if (window.scrollY > 250 && typeof globalData !== 'undefined' && globalData && globalData.ticker) {
            stickyBanner.classList.add('visible');
            document.body.classList.add('banner-visible');
        } else {
            stickyBanner.classList.remove('visible');
            document.body.classList.remove('banner-visible');
        }
    });

    // --- FIREBASE CLOUD SYNC ---
    let currentUser = null;
    let db = null;
    let _syncInProgress = false;

    if (window.firebase) {
        const loginBtn = document.getElementById('login-btn');
        if (loginBtn) {
            loginBtn.title = `Sync Connecting...`;
            loginBtn.classList.remove('logged-in');
        }

        fetch('/api/firebase-config')
            .then(res => {
                if (!res.ok) throw new Error("API returned " + res.status);
                return res.json();
            })
            .then(config => {
                firebase.initializeApp(config);
                return firebase.auth().setPersistence(firebase.auth.Auth.Persistence.LOCAL);
            })
            .then(() => {
                db = firebase.firestore();

                firebase.auth().getRedirectResult().catch(err => {
                    const authError = document.getElementById('auth-error');
                    const authModal = document.getElementById('auth-modal');
                    if (authError && err.code !== 'auth/redirect-cancelled-by-user') {
                        authError.textContent = err.message;
                        authError.style.display = 'block';
                        if (authModal) authModal.style.display = 'flex';
                    }
                });

                firebase.auth().onAuthStateChanged((user) => {
                    currentUser = user;
                    if (loginBtn) {
                        if (user) {
                            loginBtn.classList.add('logged-in');
                            loginBtn.title = `Sync ON: ${user.email ? user.email.split('@')[0] : 'User'}`;
                            syncFromCloud(); // Pull data from cloud on login
                        } else {
                            loginBtn.classList.remove('logged-in');
                            loginBtn.title = `Login to Sync`;
                        }
                    }
                });
            })
            .catch(err => {
                console.error("Could not initialize Firebase:", err);
                if (loginBtn) {
                    loginBtn.title = `⚠️ Sync Error (Check Server)`;
                }
            });
    }

    async function syncToCloud() {
        if (!currentUser || !db || _syncInProgress) return;
        _syncInProgress = true;
        try {
            // Gather data from localStorage
            const watchListData = JSON.parse(localStorage.getItem('fairValueWatchlist')) || [];
            const collapsedData = JSON.parse(localStorage.getItem('method_cards_collapsed')) || {};

            // Gather custom peers
            const customPeersData = {};
            for (let i = 0; i < localStorage.length; i++) {
                const k = localStorage.key(i);
                if (k && k.startsWith('customPeers_')) {
                    try {
                        customPeersData[k] = JSON.parse(localStorage.getItem(k));
                    } catch (e) { }
                }
            }

            const docRef = db.collection('users').doc(currentUser.uid);
            await docRef.set({
                fairValueWatchlist: watchListData,
                method_cards_collapsed: collapsedData,
                customPeers: customPeersData,
                lastSync: firebase.firestore.FieldValue.serverTimestamp()
            });

        } catch (error) {
            console.error("Cloud Sync Error (Push):", error);
        } finally {
            _syncInProgress = false;
        }
    }

    async function syncFromCloud() {
        if (!currentUser || !db || _syncInProgress) return;
        _syncInProgress = true;
        try {
            const docRef = db.collection('users').doc(currentUser.uid);
            const docSnap = await docRef.get();
            if (docSnap.exists) {
                const data = docSnap.data();

                if (data.fairValueWatchlist) {
                    localStorage.setItem('fairValueWatchlist', JSON.stringify(data.fairValueWatchlist));
                    if (typeof watchlist !== 'undefined') {
                        watchlist = data.fairValueWatchlist; // Update global array
                    }
                }
                if (data.method_cards_collapsed) {
                    localStorage.setItem('method_cards_collapsed', JSON.stringify(data.method_cards_collapsed));
                }
                if (data.customPeers) {
                    // Clear existing local custom peers to prevent stale data
                    const keysToRemove = [];
                    for (let i = 0; i < localStorage.length; i++) {
                        const k = localStorage.key(i);
                        if (k && k.startsWith('customPeers_')) keysToRemove.push(k);
                    }
                    keysToRemove.forEach(k => localStorage.removeItem(k));

                    // Set new peers
                    Object.keys(data.customPeers).forEach(k => {
                        localStorage.setItem(k, JSON.stringify(data.customPeers[k]));
                    });
                }

                // Refresh UI Watchlist
                if (typeof renderWatchlist === 'function') {
                    renderWatchlist();
                }
            } else {
                // First time user, push local data to cloud
                _syncInProgress = false;
                syncToCloud();
                return;
            }
        } catch (error) {
            console.error("Cloud Sync Error (Pull):", error);
        } finally {
            _syncInProgress = false;
        }
    }

    // Modal UI Handlers
    const loginBtn = document.getElementById('login-btn');
    const authModal = document.getElementById('auth-modal');
    const closeAuthBtn = document.getElementById('close-auth-modal');
    const authEmail = document.getElementById('auth-email');
    const authPass = document.getElementById('auth-password');
    const authSubmit = document.getElementById('auth-submit-btn');
    const authGoogle = document.getElementById('auth-google-btn');
    const authError = document.getElementById('auth-error');

    if (loginBtn) {
        loginBtn.addEventListener('click', () => {
            if (currentUser) {
                if (confirm("Do you want to log out?")) {
                    firebase.auth().signOut();
                }
            } else {
                authModal.style.display = 'flex';
                authError.style.display = 'none';
            }
        });
    }

    if (closeAuthBtn) {
        closeAuthBtn.addEventListener('click', () => {
            authModal.style.display = 'none';
        });
    }

    if (authSubmit && window.firebase) {
        authSubmit.addEventListener('click', async () => {
            const e = authEmail.value.trim();
            const p = authPass.value;
            if (!e || !p) {
                authError.textContent = "Enter email and password";
                authError.style.display = 'block';
                return;
            }
            authSubmit.disabled = true;
            try {
                // Try to sign in
                try {
                    await firebase.auth().signInWithEmailAndPassword(e, p);
                } catch (err) {
                    if (err.code === 'auth/user-not-found' || err.code === 'auth/invalid-credential' || err.code === 'auth/invalid-login-credentials') {
                        // Attempt to create user if not found
                        await firebase.auth().createUserWithEmailAndPassword(e, p);
                    } else {
                        throw err;
                    }
                }
                authModal.style.display = 'none';
                authEmail.value = '';
                authPass.value = '';
            } catch (err) {
                authError.textContent = err.message;
                authError.style.display = 'block';
            } finally {
                authSubmit.disabled = false;
            }
        });
    }

    if (authGoogle && window.firebase) {
        authGoogle.addEventListener('click', async () => {
            if (authGoogle.disabled) return;
            const provider = new firebase.auth.GoogleAuthProvider();
            const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

            const originalText = authGoogle.innerHTML;
            authGoogle.disabled = true;
            authGoogle.style.opacity = '0.7';
            authGoogle.innerHTML = `<img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" width="18" height="18"> Please wait...`;

            try {
                await firebase.auth().signInWithPopup(provider);
                authModal.style.display = 'none';
            } catch (err) {
                console.error("Google auth error:", err);
                if (authError && err.code !== 'auth/popup-closed-by-user') {
                    authError.textContent = err.message;
                    authError.style.display = 'block';
                }
            } finally {
                authGoogle.disabled = false;
                authGoogle.style.opacity = '1';
                authGoogle.innerHTML = originalText;
            }
        });

        // Redirect errors handled during initialization
    }

    // Wrap setItem to auto-sync
    const originalSetItem = localStorage.setItem;
    localStorage.setItem = function (key, value) {
        originalSetItem.apply(this, arguments);
        if (!_syncInProgress && (key === 'fairValueWatchlist' || key === 'method_cards_collapsed' || (key && key.startsWith('customPeers_')))) {
            syncToCloud();
        }
    };

    const originalRemoveItem = localStorage.removeItem;
    localStorage.removeItem = function (key) {
        originalRemoveItem.apply(this, arguments);
        if (!_syncInProgress && key && key.startsWith('customPeers_')) {
            syncToCloud();
        }
    };
    // --- END FIREBASE CLOUD SYNC ---

    let selectedLynchMethod = 'system'; // default

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

        const card = btn.closest('.research-card');
        if (!card) return;

        // Update buttons within the same card
        card.querySelectorAll('.analyst-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Update contents within the same card
        card.querySelectorAll('.analyst-tab-content').forEach(content => {
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
        tickerInput.addEventListener('input', function () {
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
            div.innerHTML = `
                <span class="ticker-match">${item.ticker}</span>
                <span class="name-match">${item.name}</span>
                <span class="exch-match">${item.exchange || ''}</span>
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
    window.onerror = function (message, source, lineno, colno, error) {
        console.error('GLOBAL ERROR:', message, 'at', source, ':', lineno, ':', colno);
        return false; // Let browser handle it too
    };
    window.onunhandledrejection = function (event) {
        console.error('UNHANDLED PROMISE REJECTION:', event.reason);
    };

    let currentTicker = null;
    let currentHealthBreakdown = null;
    let currentBuyBreakdown = null;
    let _originalBuyBreakdown = null;
    let _originalBuyScore = null;

    // --- Dynamic Industry PEG Calculation (v320) ---
    function recalcIndustryPeg(prof) {
        if (!prof || !prof.competitor_metrics) return;
        const validPegs = prof.competitor_metrics
            .map(p => {
                const custom = parseFloat(p.peg_custom);
                if (!isNaN(custom) && custom > 0) return custom;
                
                const basicPeg = parseFloat(p.peg_ratio);
                if (!isNaN(basicPeg) && basicPeg > 0) return basicPeg;
                
                return null;
            })
            .filter(v => v !== null && !isNaN(v) && v > 0);

        let median = null; // No fallback
        if (validPegs.length > 0) {
            validPegs.sort((a, b) => a - b);
            const mid = Math.floor(validPegs.length / 2);
            if (validPegs.length % 2 === 0) {
                median = (validPegs[mid - 1] + validPegs[mid]) / 2;
            } else {
                median = validPegs[mid];
            }
        }

        if (globalData && globalData.formula_data && globalData.formula_data.peg) {
            globalData.formula_data.peg.industry_peg = median;
        }

        // Cache the median for the sector
        if (prof.sector) {
            localStorage.setItem('sectorMedianPeg_' + prof.sector, median);
        }

        return median;
    }

    let currentPiotroskiBreakdown = null;
    let chartRevFcf = null;
    let chartEpsShares = null;
    let globalData = null;
    let _currentScenario = 'base';
let _customScenariosData = null;
window._customScenariosData = null;
    let _realApiPrice = null; // v299: Immutable anchor for Fair Value stability
    let _originalPrice = null; // Stores the restore point for simulation reset
    let _simulating = false;

// --- PRICE ANIMATION UTILITY ---
const animatePriceUI = (openPrice, newPrice, triggerFlash = true) => {
    if (!openPrice || openPrice === newPrice) {
        const ti = document.getElementById('price-trend-icon');
        if (ti) ti.textContent = '';
        const sti = document.getElementById('sticky-price-trend-icon');
        if (sti) sti.textContent = '';
        return;
    }

    const priceEl = document.getElementById('current-price');
    const stickyPrice = document.getElementById('sticky-banner-price');
    const trendIcon = document.getElementById('price-trend-icon');
    const stickyTrendIcon = document.getElementById('sticky-price-trend-icon');

    const isUp = newPrice > openPrice;
    const color = isUp ? '#10b981' : '#ef4444';
    const icon = isUp ? '▲' : '▼';
    const pulseClass = isUp ? 'price-flash-green' : 'price-flash-red';

    if (trendIcon && !_simulating) {
        trendIcon.textContent = icon;
        trendIcon.style.color = color;
    }
    if (stickyTrendIcon && !_simulating) {
        stickyTrendIcon.textContent = icon;
        stickyTrendIcon.style.color = color;
    }

    if (triggerFlash && priceEl && !_simulating) {
        priceEl.classList.remove('price-flash-green', 'price-flash-red');
        void priceEl.offsetWidth; // trigger reflow
        priceEl.classList.add(pulseClass);
    }
    if (triggerFlash && stickyPrice && !_simulating) {
        stickyPrice.classList.remove('price-flash-green', 'price-flash-red');
        void stickyPrice.offsetWidth;
        stickyPrice.classList.add(pulseClass);
    }
};



    // --- CHART TOGGLE ENGINE ---
    let _chartViewActive = false;
    let _tvWidgetCreatedFor = null;

    const initChartToggle = () => {
        const toggleBtn = document.getElementById('toggle-chart-btn');
        const viewA = document.getElementById('view-fair-value');
        const viewB = document.getElementById('view-price-chart');
        const container = document.getElementById('tv-widget-container');

        if (!toggleBtn || !viewA || !viewB) return;

        toggleBtn.onclick = () => {
            _chartViewActive = !_chartViewActive;

            const openWeightsBtn = document.getElementById('open-weights-btn');

            if (_chartViewActive) {
                // Switch to Chart View
                toggleBtn.style.background = 'rgba(251, 191, 36, 0.2)'; // Highlight active state
                toggleBtn.style.borderColor = 'rgba(251, 191, 36, 0.5)';
                viewA.style.opacity = '0';
                if (openWeightsBtn) openWeightsBtn.style.display = 'none';

                setTimeout(() => {
                    viewA.style.display = 'none';
                    viewB.style.display = 'block';
                    // give the box enough height to render the chart properly
                    const fvBox = viewA.closest('.fair-value-box');
                    if (fvBox) fvBox.style.minHeight = '350px';

                    // force reflow
                    void viewB.offsetWidth;
                    viewB.style.opacity = '1';

                    // Inject TradingView widget if needed
                    if (globalData && globalData.ticker && _tvWidgetCreatedFor !== globalData.ticker) {
                        container.innerHTML = ''; // clear old widget
                        const script = document.createElement('script');
                        script.type = 'text/javascript';
                        script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js';
                        script.async = true;

                        // Handle formatting (e.g. standardizing for TV)
                        let tvSymbol = globalData.ticker.toUpperCase();
                        if (tvSymbol.endsWith('.DE')) tvSymbol = 'XETR:' + tvSymbol.replace('.DE', '');
                        else if (tvSymbol.endsWith('.L')) tvSymbol = 'LSE:' + tvSymbol.replace('.L', '');
                        else if (tvSymbol.endsWith('.PA')) tvSymbol = 'EURONEXT:' + tvSymbol.replace('.PA', '');
                        else if (tvSymbol.endsWith('.TO')) tvSymbol = 'TSX:' + tvSymbol.replace('.TO', '');
                        else if (tvSymbol.endsWith('.AS')) tvSymbol = 'EURONEXT:' + tvSymbol.replace('.AS', '');
                        else if (tvSymbol.endsWith('.MI')) tvSymbol = 'MIL:' + tvSymbol.replace('.MI', '');
                        else if (tvSymbol.endsWith('.MC')) tvSymbol = 'BME:' + tvSymbol.replace('.MC', '');
                        else if (tvSymbol.endsWith('.SW')) tvSymbol = 'SIX:' + tvSymbol.replace('.SW', '');

                        script.innerHTML = JSON.stringify({
                            "symbols": [
                                [tvSymbol, tvSymbol + "|1D"]
                            ],
                            "chartOnly": false,
                            "width": "100%",
                            "height": "100%",
                            "locale": "en",
                            "colorTheme": "dark",
                            "showVolume": false,
                            "showMA": false,
                            "hideDateRanges": false,
                            "hideMarketStatus": false,
                            "hideSymbolLogo": true,
                            "scalePosition": "right",
                            "scaleMode": "Normal",
                            "fontFamily": "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif",
                            "fontSize": "10",
                            "noTimeScale": false,
                            "valuesTracking": "1",
                            "changeMode": "price-and-percent",
                            "chartType": "area",
                            "maLineColor": "#2962FF",
                            "maLineWidth": 1,
                            "maLength": 9,
                            "lineWidth": 2,
                            "lineType": 0,
                            "dateRanges": ["1d|1", "1m|30", "3m|60", "12m|1D", "60m|1W", "all|1M"],
                            "backgroundColor": "rgba(0, 0, 0, 0)" // transparent
                        });
                        container.appendChild(script);
                        _tvWidgetCreatedFor = globalData.ticker;
                    }
                }, 300);
            } else {
                // Switch to Current Price View
                toggleBtn.style.background = 'rgba(255,255,255,0.05)';
                toggleBtn.style.borderColor = 'rgba(255,255,255,0.1)';
                viewB.style.opacity = '0';
                if (openWeightsBtn) openWeightsBtn.style.display = 'block';

                setTimeout(() => {
                    viewB.style.display = 'none';
                    viewA.style.display = 'flex';
                    const fvBox = viewA.closest('.fair-value-box');
                    if (fvBox) fvBox.style.minHeight = '';
                    // force reflow
                    void viewA.offsetWidth;
                    viewA.style.opacity = '1';
                }, 300);
            }
        };
    };

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

                    // Restore original Buy Score and Breakdown to 100% exact original values (v308 Fix)
                    if (_originalBuyBreakdown && _originalBuyScore !== null) {
                        currentBuyBreakdown = JSON.parse(JSON.stringify(_originalBuyBreakdown));
                        globalData.buy_breakdown = currentBuyBreakdown;
                        globalData.good_to_buy_total = _originalBuyScore;

                        // Re-render profile section (restores all DOM metric values and styling)
                        if (window._renderProfile) {
                            window._renderProfile();
                        }

                        // Update UI
                        updateScoreUI(globalData.good_to_buy_total, 'buy-score-circle', 'buy-score-fill');

                        // If score breakdown modal is open, refresh it
                        const scoreModal = document.getElementById('score-modal');
                        if (scoreModal && scoreModal.style.display === 'flex') {
                            const titleEl = document.getElementById('score-modal-title');
                            if (titleEl && titleEl.textContent.includes('Good to Buy')) {
                                renderScoreBreakdown('Good to Buy Score Breakdown', globalData.good_to_buy_total, currentBuyBreakdown);
                            }
                        }
                    } else {
                        recalcWithSimPrice(_originalPrice);
                    }

                    // Trigger global recalculate callback if exists
                    if (window.triggerRecalculate) {
                        window.triggerRecalculate();
                    }
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

    const recalcWithSimPrice = (simPrice, skipTrigger = false) => {
        if (!globalData || !globalData.company_profile) return;

        if (_simulating) {
            window._simulatedPriceActive = simPrice;
        } else {
            window._simulatedPriceActive = null;
        }

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
        const newGaapPE = (prof.gaap_eps_fy > 0) ? simPrice / prof.gaap_eps_fy : 0;
        const newNonGaapPE = (prof.adjusted_eps > 0) ? simPrice / prof.adjusted_eps : 0;
        const scoringPE = (eps > 0) ? simPrice / eps : 0; // Use anchored EPS for scoring (v72 logic)

        const newPS = (revenue > 0 && shares > 0) ? simPrice / (revenue / shares) : ((prof.ps_ratio && _realApiPrice > 0) ? prof.ps_ratio * (simPrice / _realApiPrice) : 0);
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
        updateMetric('pegaap', newGaapPE > 0 ? newGaapPE.toFixed(2) + 'x' : 'N/A');
        updateMetric('penongaap', newNonGaapPE > 0 ? newNonGaapPE.toFixed(2) + 'x' : 'N/A');

        let dynFwdEpsTop = prof.fwd_eps;
        if (globalData.eps_estimates) {
            const eEstsTop = globalData.eps_estimates.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
            if (eEstsTop.length >= 1) {
                if (_currentScenario === 'bear') dynFwdEpsTop = eEstsTop[0].low ?? eEstsTop[0].avg;
                else if (_currentScenario === 'bull') dynFwdEpsTop = eEstsTop[0].high ?? eEstsTop[0].avg;
                else dynFwdEpsTop = eEstsTop[0].avg;
            }
        }
        const newPeFwd = dynFwdEpsTop > 0 ? simPrice / dynFwdEpsTop : 0;
        updateMetric('pefwd', newPeFwd > 0 ? newPeFwd.toFixed(2) + 'x' : 'N/A');
        updateMetric('5yavgpe', prof.historic_pe ? prof.historic_pe.toFixed(2) + 'x' : 'N/A');

        let pegUsedGrowth = prof.earnings_growth || 0;
        let strictCagrMode = false;
        let fwdPe = null;

        const pegSrcEl = document.getElementById('peg-eps-source');
        if (pegSrcEl && pegSrcEl.value === 'custom') {
            const rawG = document.getElementById('peg-custom-growth').value;
            if (rawG !== '' && !isNaN(parseFloat(rawG))) {
                pegUsedGrowth = parseFloat(rawG) / 100;
            }
        } else if (pegSrcEl && pegSrcEl.value === '5ycagr') {
            pegUsedGrowth = prof.cagr_5y_custom || (globalData.formula_data && globalData.formula_data.peg && globalData.formula_data.peg.eps_growth_5y_cagr) || 0;
        } else if (pegSrcEl && pegSrcEl.value === 'analyst') {
            strictCagrMode = true;
            pegUsedGrowth = null; // Enforce strict
            const pegEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
            if (pegEsts && pegEsts.length >= 2) {
                const reportedE = globalData.eps_estimates?.find(e => e && e.status === 'reported');
                const baseEps = reportedE ? reportedE.avg : (globalData.company_profile.adjusted_eps || globalData.company_profile.trailing_eps || 0);
                if (baseEps > 0) {
                    let y1, y2;
                    if (_currentScenario === 'bear') { y1 = pegEsts[0].low ?? pegEsts[0].avg; y2 = pegEsts[1].low ?? pegEsts[1].avg; }
                    else if (_currentScenario === 'bull') { y1 = pegEsts[0].high ?? pegEsts[0].avg; y2 = pegEsts[1].high ?? pegEsts[1].avg; }
                    else { y1 = pegEsts[0].avg; y2 = pegEsts[1].avg; }

                    const g1 = (y1 / baseEps) - 1;
                    const g2 = (y2 / y1) - 1;
                    pegUsedGrowth = (g1 + g2) / 2.0;
                    fwdPe = (y1 > 0) ? (simPrice / y1) : null;
                }
            }
        } else {
            if (window._getDynamicEpsGrowth) {
                pegUsedGrowth = window._getDynamicEpsGrowth();
            } else if (globalData.formula_data && globalData.formula_data.peg) {
                pegUsedGrowth = globalData.formula_data.peg.eps_growth_estimated || pegUsedGrowth;
            }
        }

        // v319: Use Forward P/E for PEG simulation (consistent with backend's current_pe which is forward-based)
        const newPeg = (pegUsedGrowth > 0 && newPeFwd > 0) ? newPeFwd / (pegUsedGrowth * 100) : 0;
        updateMetric('peg', newPeg > 0 ? newPeg.toFixed(2) : 'N/A');

        updateMetric('ps', newPS > 0 ? newPS.toFixed(2) + 'x' : 'N/A');

        const fwd_rev_per_share = prof.fwd_ps > 0 ? (_realApiPrice / prof.fwd_ps) : 0;
        const newPsFwd = fwd_rev_per_share > 0 ? simPrice / fwd_rev_per_share : 0;
        updateMetric('fwdps', newPsFwd > 0 ? newPsFwd.toFixed(2) + 'x' : 'N/A');

        const fcfPerShare = prof.pfcf_ratio > 0 ? (_realApiPrice / prof.pfcf_ratio) : 0;
        const newPfcf = fcfPerShare > 0 ? simPrice / fcfPerShare : 0;
        updateMetric('pfcf', newPfcf > 0 ? newPfcf.toFixed(2) + 'x' : 'N/A');

        updateMetric('dividendyield', formatSafePct(newDivYield));

        // --- 3. Update Current Price Header ---
        const priceEl = document.getElementById('current-price');
        let prevPrice = null;
        if (priceEl && !_simulating) {
            const prevStr = priceEl.textContent.replace(/[^0-9.-]+/g,"");
            if (prevStr) prevPrice = parseFloat(prevStr);
            priceEl.textContent = formatCurrency(simPrice);
        }

        const stickyPrice = document.getElementById('sticky-banner-price');
        if (stickyPrice) {
            stickyPrice.textContent = formatCurrency(simPrice);
            stickyPrice.style.color = _simulating ? '#fbbf24' : 'var(--accent)';
        }

        if (!_simulating && globalData && globalData.company_profile && globalData.company_profile.open_price) {
             const openPrice = globalData.company_profile.open_price;
             const priceChanged = prevPrice !== null && simPrice !== prevPrice;
             animatePriceUI(openPrice, simPrice, priceChanged);
        } else if (_simulating) {
             // Clear icons when simulating
             const ti = document.getElementById('price-trend-icon');
             if (ti) ti.textContent = '';
             const sti = document.getElementById('sticky-price-trend-icon');
             if (sti) sti.textContent = '';
        }

        // Precise growth rate calculation for simulation scoring to prevent drift
        const growthForScoring = pegUsedGrowth > 0 ? pegUsedGrowth * 100.0 : cleanPercent(prof.revenue_growth || 10);

        // --- 4. Predictive Scoring Logic (v70: Matches backend scoring.py thresholds) ---
        if (currentBuyBreakdown) {
            currentBuyBreakdown.forEach((item, _idx) => {
                const metric = item.metric || '';
                let newPts = item.points_awarded;

                // Sector detection (matches scoring.py logic)
                const industry = (prof.industry || globalData.industry || '').toLowerCase();
                const sector = (prof.sector || globalData.sector || '').toLowerCase();

                let isBank = industry.includes('bank') || industry.includes('savings');
                const isFin = sector.includes('financial');

                // Fintech Sync
                const hasBankLeverage = (globalData.health_breakdown || []).some(m => m.metric.includes('Bank Leverage'));
                const isFintech = hasBankLeverage;
                if (isFintech) isBank = false;

                const isPaymentNetwork = (industry.includes('credit services') && !isFintech && !isBank);

                const isInsurance = industry.includes('insurance');
                const isREIT = sector.includes('real estate') || sector.includes('reit');
                const isEnergy = sector.includes('energy') || sector.includes('basic materials') || sector.includes('materials');
                const isUtilities = sector.includes('utilities') || sector.includes('telecommunication') || industry.includes('telecom');
                const isDefensive = sector.includes('consumer defensive') || sector.includes('staples') || sector.includes('healthcare') || sector.includes('health care');
                const isTech = sector.includes('technology') || sector.includes('communication services') || industry.includes('software') || industry.includes('internet');

                // Extract simulation anchors
                let eps_5yr_g = cleanPercent(globalData.company_profile.eps_growth_5y_consensus || globalData.company_profile.eps_5yr_growth);
                let rev_g_val = cleanPercent(globalData.company_profile.revenue_growth || 0);

                let dynFwdEpsTop = prof.fwd_eps || 0;
                let dynFwdRevTop = prof.forward_revenue || 0;
                if (globalData.eps_estimates) {
                    const eEstsTop = globalData.eps_estimates.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
                    if (eEstsTop.length >= 2) {
                        if (_currentScenario === 'bear') dynFwdEpsTop = ((eEstsTop[0].low ?? eEstsTop[0].avg) + (eEstsTop[1].low ?? eEstsTop[1].avg)) / 2.0;
                        else if (_currentScenario === 'bull') dynFwdEpsTop = ((eEstsTop[0].high ?? eEstsTop[0].avg) + (eEstsTop[1].high ?? eEstsTop[1].avg)) / 2.0;
                        else dynFwdEpsTop = (eEstsTop[0].avg + eEstsTop[1].avg) / 2.0;
                    } else if (eEstsTop.length === 1) {
                        if (_currentScenario === 'bear') dynFwdEpsTop = eEstsTop[0].low ?? eEstsTop[0].avg;
                        else if (_currentScenario === 'bull') dynFwdEpsTop = eEstsTop[0].high ?? eEstsTop[0].avg;
                        else dynFwdEpsTop = eEstsTop[0].avg;
                    }
                }
                if (globalData.rev_estimates) {
                    const rEstsTop = globalData.rev_estimates.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
                    if (rEstsTop.length >= 2) {
                        if (_currentScenario === 'bear') dynFwdRevTop = ((rEstsTop[0].low ?? rEstsTop[0].avg) + (rEstsTop[1].low ?? rEstsTop[1].avg)) / 2.0;
                        else if (_currentScenario === 'bull') dynFwdRevTop = ((rEstsTop[0].high ?? rEstsTop[0].avg) + (rEstsTop[1].high ?? rEstsTop[1].avg)) / 2.0;
                        else dynFwdRevTop = (rEstsTop[0].avg + rEstsTop[1].avg) / 2.0;
                    } else if (rEstsTop.length === 1) {
                        if (_currentScenario === 'bear') dynFwdRevTop = rEstsTop[0].low ?? rEstsTop[0].avg;
                        else if (_currentScenario === 'bull') dynFwdRevTop = rEstsTop[0].high ?? rEstsTop[0].avg;
                        else dynFwdRevTop = rEstsTop[0].avg;
                    }
                }

                let dynFwdEbitda = (globalData.ebitda || 0);
                if ((globalData.revenue || 0) > 0) {
                    dynFwdEbitda = dynFwdRevTop * ((globalData.ebitda || 0) / globalData.revenue);
                }
                const newEvEbitda = (dynFwdEbitda > 0) ? ev / dynFwdEbitda : 0;
                const dynPS = (dynFwdRevTop > 0 && shares > 0) ? simPrice / (dynFwdRevTop / shares) : newPS;

                let dynamicEpsGrowth = eps_5yr_g;
                if (prof.trailing_eps && prof.trailing_eps !== 0) {
                    dynamicEpsGrowth = ((dynFwdEpsTop - prof.trailing_eps) / Math.abs(prof.trailing_eps)) * 100;
                }
                let dynamicRevGrowth = rev_g_val;
                if (globalData.revenue && globalData.revenue !== 0) {
                    dynamicRevGrowth = ((dynFwdRevTop - globalData.revenue) / Math.abs(globalData.revenue)) * 100;
                }

                let revUsedGrowth = 0;
                if (window._getDynamicRevGrowth) {
                    revUsedGrowth = window._getDynamicRevGrowth();
                }

                const fwd_growth = (pegUsedGrowth > 0) ? (pegUsedGrowth < 1.0 ? pegUsedGrowth * 100 : pegUsedGrowth) : dynamicEpsGrowth;
                let rev_fwd_growth = (revUsedGrowth > 0) ? (revUsedGrowth < 1.0 ? revUsedGrowth * 100 : revUsedGrowth) : dynamicRevGrowth;

                let activePE = 0;
                let activeEV = 0;
                let activePS = 0;
                let activePB = 0;
                let activePAFFO = 0;

                // Use backend's exact metric value, scaled mathematically by the price change!
                const origItem = (_originalBuyBreakdown && _originalBuyBreakdown[_idx]) ? _originalBuyBreakdown[_idx] : item;
                let backendVal = parseFloat((origItem.value || '').replace(/[^\d.-]/g, ''));
                if (isNaN(backendVal)) backendVal = 0;

                if (metric.includes('P/E Ratio')) {
                    if (backendVal <= 0) backendVal = parseFloat(globalData.fwd_pe) || parseFloat(globalData.forward_pe) || 0;
                    if (backendVal > 0 && _realApiPrice > 0) activePE = backendVal * (simPrice / _realApiPrice);
                } else if (metric.includes('EV/EBITDA') || metric.includes('EV / EBITDA')) {
                    if (backendVal <= 0 && globalData.ebitda > 0) backendVal = (globalData.market_cap + (globalData.total_debt || 0) - (globalData.total_cash || 0)) / globalData.ebitda;
                    if (backendVal > 0 && _realApiPrice > 0) activeEV = backendVal * (simPrice / _realApiPrice);
                } else if (metric.includes('Price-to-Book')) {
                    if (backendVal <= 0) backendVal = globalData.price_to_book || 0;
                    if (backendVal > 0 && _realApiPrice > 0) activePB = backendVal * (simPrice / _realApiPrice);
                } else if (metric.includes('P/S Ratio')) {
                    if (backendVal <= 0) backendVal = globalData.company_profile?.ps_ratio || 0;
                    if (backendVal > 0 && _realApiPrice > 0) activePS = backendVal * (simPrice / _realApiPrice);
                } else if (metric.includes('P/AFFO')) {
                    if (backendVal <= 0) backendVal = globalData.company_profile?.price_to_affo || 0;
                    if (backendVal > 0 && _realApiPrice > 0) activePAFFO = backendVal * (simPrice / _realApiPrice);
                }

                // Fallbacks just in case
                if (activePE === 0 && scoringPE > 0) activePE = scoringPE;
                if (activeEV === 0 && newEvEbitda > 0) activeEV = newEvEbitda;
                if (activePS === 0 && dynPS > 0) activePS = dynPS;
                if (activePB === 0 && newPB > 0) activePB = newPB;

                if (window._renderProfile) window._renderProfile();

                // Guard Clause Universal
                if ((metric.includes('P/E Ratio') || (metric.includes('EV/EBITDA') || metric.includes('EV / EBITDA')) || metric.includes('P/S Ratio') || metric.includes('Price-to-Book') || (metric.includes('P/AFFO') || metric.includes('P/AFFO'))) && (activePE < 0 || activeEV < 0 || activePS < 0 || activePB < 0)) {
                    // handled below per metric, but generally 0 pts
                }

                if (metric.includes('Margin of Safety')) {
                    item.metric = 'Margin of Safety (Fair Value)';
                    if (isFintech) {
                        newPts = (newMos > 25) ? 30 : ((newMos >= 0) ? 15 : 0);
                    } else if (isBank || isFin || isInsurance || isREIT) {
                        newPts = (newMos > 20) ? 30 : ((newMos > 5) ? 15 : 0);
                    } else if (isTech || isDefensive) {
                        newPts = (newMos > 10) ? 30 : ((newMos > 0) ? 30 * (14.9 / 25.0) : (newMos >= -10 ? 12 : 0));
                    } else {
                        newPts = (newMos > 15) ? 30 : ((newMos > 5) ? 30 * (14.9 / 25.0) : (newMos >= -5 ? 12 : 0));
                    }
                    item.value = formatPercent(newMos);
                } else if (metric.includes('P/E Ratio')) {
                    let pts = 0;
                    const roicVal = cleanPercent(globalData.company_profile?.roic || 0);
                    const healthScore = globalData.health_score_total || 0;
                    const isMonopoly = (roicVal > 20.0 && healthScore >= 70);
                    const histPE = parseFloat(globalData.company_profile?.historic_pe) || parseFloat(globalData.pe_historic) || 0;

                    if (activePE > 0) {
                        if (isMonopoly && histPE > 0) {
                            const maxPts = item.max_points || 20;
                            const discount = ((histPE - activePE) / histPE) * 100.0;
                            if (discount >= 25.0) pts = maxPts;
                            else if (discount >= 15.0) pts = maxPts * 0.75;
                            else if (discount >= 10.0) pts = maxPts * 0.50;
                            else if (discount > 0.0) pts = maxPts * 0.25;
                            else pts = 0;
                        } else if (isFintech) {
                            if (activePE <= 25) pts = 20;
                            else if (activePE <= 40) pts = 10;
                        } else if (isFin && isBank) {
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
                                if (peg > 0 && peg <= 1.2 && rev_fwd_growth >= 20.0) pts = 10;
                            }
                        } else if (isPaymentNetwork) {
                            if (activePE <= 28) pts = 20;
                            else if (activePE <= 35) pts = 10;
                        } else {
                            // Industrials
                            if (activePE <= 18) pts = 20;
                            else if (activePE <= 22) pts = 10;
                            if (pts === 0 && activePE > 0 && pegUsedGrowth > 0) {
                                const peg = activePE / (fwd_growth);
                                if (peg > 0 && peg <= 1.2 && rev_fwd_growth >= 15.0) pts = 10;
                            }
                        }
                    }
                    newPts = pts;
                    item.value = activePE > 0 ? activePE.toFixed(2) + 'x' : '0.00x';
                } else if ((metric.includes('EV/EBITDA') || metric.includes('EV / EBITDA'))) {
                    let pts = 0;
                    if (activeEV > 0) {
                        if (isEnergy) {
                            if (activeEV <= 6.0) pts = 20;
                            else if (activeEV <= 9.0) pts = 10;
                        } else if (isUtilities) {
                            if (activeEV <= 10.0) pts = 20;
                            else if (activeEV <= 14.0) pts = 10;
                        } else if (isDefensive) {
                            if (activeEV <= 14.0) pts = 15;
                            else if (activeEV <= 18.0) pts = 7.5;
                            if (pts === 0 && activeEV > 0 && pegUsedGrowth > 0) {
                                const peg = activePE / (fwd_growth);
                                if (peg > 0 && peg <= 1.2 && fwd_growth >= 15.0) pts = 7.5;
                            }
                        } else if (isTech) {
                            if (activeEV <= 18.0) pts = 10;
                            else if (activeEV <= 25.0) pts = 5;
                            if (pts === 0 && activeEV > 0 && pegUsedGrowth > 0) {
                                const peg = activePE / (fwd_growth);
                                if (peg > 0 && peg <= 1.2 && rev_fwd_growth >= 20.0) pts = 5;
                            }
                        } else if (isPaymentNetwork) {
                            if (activeEV <= 20.0) pts = 15;
                            else if (activeEV <= 25.0) pts = 7.5;
                        } else {
                            if (activeEV <= 12.0) pts = 15;
                            else if (activeEV <= 16.0) pts = 7.5;
                            if (pts === 0 && activeEV > 0 && pegUsedGrowth > 0) {
                                const peg = activePE / (fwd_growth);
                                if (peg > 0 && peg <= 1.2 && rev_fwd_growth >= 15.0) pts = 5;
                            }
                        }
                    }
                    newPts = pts;
                    item.value = activeEV > 0 ? activeEV.toFixed(2) + 'x' : '0.00x';
                } else if (metric.includes('Price-to-Book')) {
                    let pts = 0;
                    if (activePB > 0) {
                        if (isFintech) {
                            if (activePB <= 3.5) pts = 15;
                            else if (activePB <= 6.0) pts = 7.5;
                        } else if (isFin && isBank) {
                            if (activePB < 1.5) pts = 20;
                            else if (activePB <= 2.0) pts = 10;
                        } else if (isInsurance) {
                            if (activePB < 1.5) pts = 25;
                            else if (activePB <= 2.0) pts = 12.5;
                        } else if (isEnergy) {
                            if (activePB <= 1.5) pts = 20;
                            else if (activePB <= 2.5) pts = 10;
                        } else {
                            if (activePB <= 2.0) pts = 10;
                            else if (activePB <= 3.0) pts = 5;
                        }
                    }
                    newPts = pts;
                    item.value = activePB > 0 ? activePB.toFixed(2) + 'x' : '0.00x';
                } else if (metric.includes('P/S Ratio')) {
                    const target_pe = getTargetPe(sector, industry);
                    const ebitM = cleanPercent(globalData.company_profile.ebit_margin || 0);
                    const ebitdaM = cleanPercent(globalData.company_profile.ebitda_margin || 0);
                    const netM = cleanPercent(globalData.company_profile.net_profit_margin || 0);
                    const margin = netM > 0 ? netM : (ebitM > 0 ? ebitM : ebitdaM);

                    const target_ps = margin > 0 ? (target_pe * (margin / 100)) : 1.5;
                    let pts = 0;
                    if (activePS > 0) {
                        if (margin > 20) {
                            if (activePS <= target_ps) pts = 10;
                            else if (activePS <= target_ps * 1.5) pts = 5;
                        } else if (margin > 0) {
                            if (activePS <= target_ps) pts = 10;
                            else if (activePS <= target_ps * 1.5) pts = 5;
                        } else if (margin < 0) {
                            if (rev_fwd_growth > 20 && activePS <= 5.0) pts = 5;
                        }
                    }
                    newPts = pts;
                    item.value = activePS > 0 ? activePS.toFixed(2) + 'x' : '0.00x';
                } else if (metric.includes('Dividend Yield')) {
                    const dyPct = newDivYield * 100;
                    if (isREIT) newPts = dyPct > 5 ? 15 : (dyPct >= 3 ? 7.5 : 0);
                    else if (isFin && isBank) newPts = dyPct > 3 ? 15 : (dyPct >= 1.5 ? 7.5 : 0);
                    else if (isInsurance) newPts = dyPct > 3 ? 15 : (dyPct >= 1.5 ? 7.5 : 0);
                    else if (isEnergy) newPts = dyPct > 4 ? 15 : (dyPct >= 2 ? 7.5 : 0);
                    else if (isUtilities) newPts = dyPct > 4 ? 25 : (dyPct >= 2.5 ? 12.5 : 0);
                    else newPts = 0;
                    item.value = dyPct.toFixed(1) + '%';
                } else if (metric.includes('PEG Ratio')) {
                    let newPEG = (typeof currentFormulaData !== 'undefined' && currentFormulaData && currentFormulaData.peg && currentFormulaData.peg.dynamic_peg != null) 
                        ? currentFormulaData.peg.dynamic_peg 
                        : 0;

                    if (newPEG <= 0) {
                        if (backendVal <= 0) backendVal = globalData.company_profile?.peg_ratio || 0;
                        if (backendVal > 0 && _realApiPrice > 0) {
                            newPEG = backendVal * (simPrice / _realApiPrice);
                        } else if (fwd_growth > 0 && activePE > 0) {
                            newPEG = activePE / fwd_growth;
                        }
                    }
                    if (isFintech) newPts = (newPEG > 0 && newPEG <= 1.2) ? 15 : ((newPEG > 0 && newPEG <= 2.0) ? 7.5 : 0);
                    else if (isPaymentNetwork) newPts = (newPEG > 0 && newPEG <= 1.6) ? 15 : ((newPEG > 0 && newPEG <= 2.2) ? 7.5 : 0);
                    else if (isDefensive) newPts = (newPEG > 0 && newPEG < 1.5) ? 20 : ((newPEG > 0 && newPEG <= 2.0) ? 10 : 0);
                    else if (isTech) newPts = (newPEG > 0 && newPEG < 1.5) ? 10 : ((newPEG > 0 && newPEG <= 2.0) ? 5 : 0);
                    else newPts = (newPEG > 0 && newPEG < 1.0) ? 10 : ((newPEG > 0 && newPEG <= 1.5) ? 5 : 0);
                    item.value = newPEG > 0 ? newPEG.toFixed(2) + 'x' : '0.00x';
                } else if ((metric.includes('P/AFFO') || metric.includes('P/AFFO'))) {
                    let pts = 0;
                    if (activePAFFO > 0) {
                        if (activePAFFO <= 15) pts = 20;
                        else if (activePAFFO <= 18) pts = 10;
                    }
                    newPts = pts;
                    item.value = activePAFFO > 0 ? activePAFFO.toFixed(2) + 'x' : '0.00x';
                } else if (metric.includes('Rule of 40')) {
                    const currentScoring = globalData.scoring_results ? globalData.scoring_results[_currentScenario || 'base'] : null;
                    const r40Data = (currentScoring && currentScoring.rule_of_40) ? currentScoring.rule_of_40 : globalData.rule_of_40;
                    if (r40Data && r40Data.total !== undefined) {
                        item.value = r40Data.total.toFixed(1) + '%';
                        newPts = r40Data.total >= 40 ? 30 : (r40Data.total >= 30 ? 15 : 0);
                    }
                } else if (metric.includes('Rev Growth') || metric.includes('EPS Growth') || metric.includes('AFFO Growth') || metric.includes('Revenue Growth')) {
                    if (metric.includes('Revenue Growth')) {
                        item.value = rev_fwd_growth > 0 ? rev_fwd_growth.toFixed(1) + '%' : '0.0%';
                        if (isFintech) {
                            if (rev_fwd_growth > 25) newPts = 20;
                            else if (rev_fwd_growth >= 10) newPts = 10;
                            else newPts = 0;
                        } else if (isTech) {
                            if (rev_fwd_growth > 15) newPts = 20;
                            else if (rev_fwd_growth >= 8) newPts = 10;
                            else newPts = 0;
                        } else if (isDefensive) {
                            if (rev_fwd_growth > 10) newPts = 20;
                            else if (rev_fwd_growth >= 5) newPts = 10;
                            else newPts = 0;
                        }
                    } else if (metric.includes('AFFO Growth')) {
                        item.value = fwd_growth > 0 ? fwd_growth.toFixed(1) + '%' : '0.0%';
                        if (fwd_growth > 8) newPts = 20;
                        else if (fwd_growth >= 3) newPts = 10;
                        else newPts = 0;
                    } else { // EPS Growth
                        item.value = fwd_growth > 0 ? fwd_growth.toFixed(1) + '%' : '0.0%';
                        if (isFin && isBank) {
                            if (fwd_growth > 7) newPts = 10;
                            else if (fwd_growth >= 3) newPts = 5;
                            else newPts = 0;
                        } else if (isInsurance) {
                            if (fwd_growth > 8) newPts = 10;
                            else if (fwd_growth >= 4) newPts = 5;
                            else newPts = 0;
                        } else if (isTech || isDefensive) {
                            if (fwd_growth > 15) newPts = 15;
                            else if (fwd_growth >= 8) newPts = 7.5;
                            else newPts = 0;
                        } else {
                            if (fwd_growth > 10) newPts = 10;
                            else if (fwd_growth >= 5) newPts = 5;
                            else newPts = 0;
                        }
                    }
                }

                item.points_awarded = Math.min(newPts, item.max_points);
            });
        }

        // --- 5. Global Visual Re-sync ---
        if (window.triggerRecalculate && !skipTrigger) {
            window.triggerRecalculate();
        }

        // --- 6. Refresh Score Dashboard ---
        const totalBuy = currentBuyBreakdown.reduce((sum, item) => sum + (item.points_awarded || 0), 0);
        globalData.good_to_buy_total = Math.round(Math.min(Math.max(totalBuy, 0), 100));
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
        const strengths = allMetrics.filter(m => m.points_awarded === m.max_points && m.max_points > 0).sort((a, b) => b.max_points - a.max_points);
        const risks = allMetrics.filter(m => m.points_awarded === 0 && m.max_points > 0).sort((a, b) => b.max_points - a.max_points);

        const sList = document.getElementById('top-strengths-list');
        if (sList) {
            sList.innerHTML = strengths.slice(0, 3).map(s => `<li>${s.metric}: ${s.value}</li>`).join('');
        }
        const rList = document.getElementById('risk-factors-list');
        if (rList) {
            rList.innerHTML = risks.slice(0, 3).map(r => `<li>${r.metric}: ${r.value}</li>`).join('');
        }
    };

    // Custom Weights Logic (v34: Now ticker-specific via overrides)
    let customWeights = { dcf: 25, peg: 25, relative: 25, lynch: 25 };

    // Watchlist State (already initialized at the top of the file)

    // Non-destructive Watchlist Merge (v37: Fixed sync-back loop and added error protection)
    fetch('/api/watchlist?t=' + new Date().getTime(), { cache: 'no-store' })
        .then(r => {
            if (!r.ok) throw new Error('Watchlist sync unreachable');
            return r.json();
        })
        .then(serverData => {
            if (Array.isArray(serverData)) {
                const localData = JSON.parse(localStorage.getItem('fairValueWatchlist')) || [];
                // Server is the single source of truth. Prevents deleted items from resurrecting across devices.
                const hasChanged = JSON.stringify(watchlist) !== JSON.stringify(serverData);
                watchlist = serverData;
                localStorage.setItem('fairValueWatchlist', JSON.stringify(watchlist));

                // If the local device had an outdated list, we DO NOT sync back to the server.
                // We just accepted the server's list.
                // Sync-back is only triggered intentionally by user actions (add/remove).

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
        // v319: Migration to clear stale weights for MA/V that got cached as 0 DCF before the backend fix
        if (!localStorage.getItem('v319_weights_migrated')) {
            for (const tk of Object.keys(cachedOverrides)) {
                if (cachedOverrides[tk] && cachedOverrides[tk].weights) {
                    cachedOverrides[tk]._v319_stale = true;
                }
            }
            localStorage.setItem('v319_weights_migrated', 'true');
            console.log('v319: Marked all existing weight overrides as stale for archetype migration.');
        }
    }).catch(e => console.error('Overrides load error:', e));

    // v315: Force clear old customPeers cache to apply new Forward-First backend logic
    if (!localStorage.getItem('v315_peers_reset')) {
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i);
            if (k && k.startsWith('customPeers_')) {
                keysToRemove.push(k);
            }
        }
        keysToRemove.forEach(k => localStorage.removeItem(k));
        localStorage.setItem('v315_peers_reset', 'true');
        console.log('Cleared old custom peers cache to apply new FWD logic.');
    }

    const getSmartWeights = (sector, industry, archetypeWeights) => {
        // v316: If backend provides archetype-determined weights, use them directly
        if (archetypeWeights && typeof archetypeWeights === 'object') {
            return {
                dcf: archetypeWeights.dcf || 0,
                peg: archetypeWeights.peg || 0,
                relative: archetypeWeights.relative || 0,
                lynch: archetypeWeights.lynch || 0
            };
        }
        // Fallback: sector-based weights (legacy, only used if backend doesn't provide archetypeWeights)
        let w = { dcf: 25, peg: 25, relative: 25, lynch: 25 };
        const s = (sector || '').toLowerCase();
        const ind = (industry || '').toLowerCase();

        if (s.includes('financial')) {
            const fintechKeywords = ["credit services", "financial data", "stock exchange", "capital market"];
            const isFintech = fintechKeywords.some(k => ind.includes(k));
            if (isFintech) {
                w = { dcf: 25, peg: 25, relative: 25, lynch: 25 };
            } else {
                w = { dcf: 0, peg: 10, relative: 45, lynch: 45 };
            }
        } else if (s.includes('real estate') || s.includes('reit')) {
            w = { dcf: 20, peg: 10, relative: 40, lynch: 30 };
        } else if (s.includes('technology') || s.includes('healthcare') || s.includes('health care') || s.includes('communication')) {
            w = { dcf: 25, peg: 40, relative: 25, lynch: 10 };
        } else if (s.includes('industrials') || s.includes('energy') || s.includes('basic materials') || s.includes('cyclical')) {
            w = { dcf: 30, peg: 10, relative: 40, lynch: 20 };
        } else {
            w = { dcf: 25, peg: 25, relative: 25, lynch: 25 };
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

    const setSmartWeights = (sector, industry, archetypeWeights) => {
        const w = getSmartWeights(sector, industry, archetypeWeights);
        customWeights = w;

        // Sync UI
        const dcfInput = document.getElementById('weight-dcf');
        if (dcfInput) dcfInput.value = w.dcf;
        const pegInput = document.getElementById('weight-peg');
        if (pegInput) pegInput.value = w.peg;
        const relInput = document.getElementById('weight-relative');
        if (relInput) relInput.value = w.relative;
        const lynInput = document.getElementById('weight-lynch');
        if (lynInput) lynInput.value = w.lynch;

        return w;
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
            if (currentRevenue < 0) {
                currentRevenue = currentRevenue + Math.abs(currentRevenue) * g;
            } else {
                currentRevenue *= (1 + g);
            }

            // FCF margin increases by configured growth rate each year in the background
            const yearMargin = startingFcfMargin + (i * marginGrowth);

            // FCF is calculated on top of projected Revenue
            currentFcf = currentRevenue * yearMargin;

            // Adjust shares based on buyback/dilution rate (positive = buyback, negative = dilution)
            if (buybackRate !== 0) {
                remainingShares *= (1 - buybackRate);
            }

            buybackCostPerYear.push(0);
            fcf_projections.push(currentFcf);

            const pv_fcf = currentFcf / Math.pow(1 + finalWacc, i - 0.5);
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
        if (document.getElementById('weights-modal')) return;
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
        if (fvContainer) {
            fvContainer.style.position = 'relative';
            const btnHtml = `<button id="open-weights-btn" title="Adjust Valuation Weights" style="position:absolute; top:15px; right:15px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:4px; font-size:1.1rem; padding:4px 8px; cursor:pointer; transition:0.2s; display:block; z-index:50;">⚖️</button>`;
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
            if (!globalData || !globalData.company_profile) return;
            setSmartWeights(globalData.company_profile.sector, globalData.company_profile.industry, globalData.archetype_weights);
            saveOverride(currentTicker); // Persist immediately when "Auto-Set" is clicked
            if (typeof window.triggerRecalculate === 'function') {
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

            if (typeof window.triggerRecalculate === 'function') {
                window.triggerRecalculate();
            }
        });
    };
    injectWeightsUI();

    // INJECT COMPARISON UI
    const injectComparisonUI = () => {
        if (document.getElementById('comparison-modal')) return;
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
        const mainPfcf = prof.pfcf_ratio;

        let dynFwdEps = prof.fwd_eps;
        let dynRevGrowth = prof.revenue_growth;
        let dynEpsGrowth = prof.earnings_growth;

        if (_currentScenario === 'bear' || _currentScenario === 'bull') {
            if (window._getDynamicEpsGrowth) dynEpsGrowth = window._getDynamicEpsGrowth();
            if (window._getDynamicRevGrowth) dynRevGrowth = window._getDynamicRevGrowth();

            // Use analyst estimates for FWD EPS directly for scenarios
            const eList = globalData.eps_estimates || [];
            const eEsts = eList.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
            if (eEsts.length >= 1) {
                if (_currentScenario === 'bear') dynFwdEps = eEsts[0].low ?? eEsts[0].avg;
                else if (_currentScenario === 'bull') dynFwdEps = eEsts[0].high ?? eEsts[0].avg;
                else dynFwdEps = eEsts[0].avg;
            } else {
                const trailingEps = prof.trailing_eps || prof.eps || 0;
                if (trailingEps > 0 && dynEpsGrowth != null) {
                    dynFwdEps = trailingEps * (1 + dynEpsGrowth);
                }
            }
        }

        const mainRev = globalData.revenue || prof.revenue;
        const mainFcfMargin = prof.fcf_margin_custom;

        const mainFwdPeCustom = prof.forward_pe_custom || (dynFwdEps > 0 ? (_realApiPrice / dynFwdEps) : null);
        const mainPegCustom = prof.peg_custom || prof.peg_ratio;

        let mainCagr5y = prof.cagr_5y_custom;

        const mainPsFwdCustom = prof.ps_forward_custom;

        let mainPfcfFwdCustom = prof.pfcf_forward_custom;

        const mainComp = {
            ticker: prof.ticker || currentTicker,
            name: prof.name || 'Current',
            market_cap: prof.market_cap,
            pe_ratio: prof.fwd_eps > 0 ? (_realApiPrice / prof.fwd_eps) : prof.trailing_pe,
            fwd_pe: dynFwdEps > 0 ? (_realApiPrice / dynFwdEps) : null,
            peg_ratio: globalData?.formula_data?.peg?.current_peg || prof.peg_ratio,
            peg_eps_type: prof.peg_eps_type,
            pe_non_gaap: (prof.adjusted_eps && prof.adjusted_eps > 0) ? (_realApiPrice / prof.adjusted_eps) : (prof.trailing_eps > 0 ? _realApiPrice / prof.trailing_eps : null),
            eps: prof.trailing_eps,
            fwd_eps: dynFwdEps,
            avg_2y_eps_growth: globalData?.formula_data?.peg?.used_growth || prof.earnings_growth,
            peg_2y_ttm: globalData?.formula_data?.peg?.current_peg || prof.peg_ratio,
            ps_ratio: prof.ps_ratio,
            revenue: mainRev,
            pfcf_ratio: mainPfcf,
            fcf: mainFcf || (prof.market_cap && mainPfcf && mainPfcf > 0 ? prof.market_cap / mainPfcf : null),
            fcf_growth: prof.historic_fcf_growth,
            margin: prof.operating_margin,
            rev_growth: dynRevGrowth,
            eps_growth: dynEpsGrowth,
            forward_pe_custom: mainFwdPeCustom,
            cagr_5y_custom: mainCagr5y,
            peg_custom: mainPegCustom,
            ps_forward_custom: mainPsFwdCustom,
            fcf_margin_custom: mainFcfMargin,
            pfcf_forward_custom: mainPfcfFwdCustom
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
            <div style="display: flex; gap: 8px; align-items: center; flex-grow: 1; max-width: 550px; flex-wrap: wrap;">
                <input id="add-peer-input" type="text" placeholder="Add Competitor (e.g. MSFT)" value="${window.fetchingPeerTicker || ''}" style="flex: 1 1 150px; padding: 8px 12px; border-radius: 6px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: white; text-transform: uppercase; font-size: 0.9rem;">
                <button id="add-peer-btn" class="peer-btn" style="margin: 0; padding: 8px 16px; flex-shrink: 0;" ${window.isFetchingPeer ? 'disabled' : ''}>${window.isFetchingPeer ? 'Fetching...' : 'Add'}</button>
                <button id="sector-peers-btn" class="peer-btn" style="margin: 0; padding: 8px 16px; flex-shrink: 0; background: rgba(56, 189, 248, 0.1); color: #38bdf8; border-color: rgba(56, 189, 248, 0.3);">🏢 Sector</button>
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
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 110px;">P/E FWD</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 110px;">5y EPS CAGR</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 100px;">PEG</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 100px;">P/S</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 110px;">P/S FWD</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 120px;">FCF Margin</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 100px;">P/FCF</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 110px;">P/FCF FWD</th>
                    <th style="padding:12px; color:white; font-size:0.85rem; min-width: 130px;">Operating Margin</th>
                </tr>
            </thead>
            <tbody>
                ${all.map((c, i) => {
            const isMain = i === 0;

            const mCap = c.market_cap || c.marketCap;

            // Backend provides pre-calculated fields, we use them to ensure consistency
            const peFwd = c.forward_pe_custom || c.fwd_pe || c.forward_pe || c.pe_ratio;
            const cagr5y = c.cagr_5y_custom;
            const peg = c.peg_custom;

            const ps = c.ps_ratio;
            const psFwd = c.ps_forward_custom;

            const fcfMargin = c.fcf_margin_custom;
            const pfcf = c.pfcf_ratio;
            const pfcfFwd = c.pfcf_forward_custom;

            const opMargin = c.margin || c.operating_margin;

            return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); background: ${isMain ? 'rgba(56, 189, 248, 0.05)' : 'transparent'};">
                        <td style="padding:12px; text-align:left; font-weight:bold; color:${isMain ? 'var(--accent)' : 'white'}; position: sticky; left: 0; background: ${isMain ? '#122238' : '#0f172a'}; z-index: 10; border-right: 1px solid rgba(255,255,255,0.1); box-shadow: 2px 0 5px rgba(0,0,0,0.2);">
                            <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                                <span>${c.ticker}</span>
                                ${!isMain ? `<span class="delete-peer-btn" data-ticker="${c.ticker}" style="cursor:pointer; color:var(--danger); font-size:1.15rem; font-weight:bold; padding: 2px 6px; transition: color 0.15s;" title="Remove Peer">&times;</span>` : ''}
                            </div>
                        </td>
                        <td style="padding:12px; font-weight:bold;">${formatBigNumber(mCap, '$')}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtPE(peFwd)}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtMargin(cagr5y)}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtPE(peg)}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtPE(ps)}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtPE(psFwd)}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtMargin(fcfMargin)}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtPE(pfcf)}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtPE(pfcfFwd)}</td>
                        <td style="padding:12px; font-weight:bold;">${fmtMargin(opMargin)}</td>
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
                } else {
                    prof.competitor_metrics = [];
                    prof.competitors = [];
                }

                recalcIndustryPeg(prof);
                updateFairValue();

                // Update UI instantly without closing modal or refreshing page
                renderComparisonModal(prof);
                displayData(globalData, true);
                document.getElementById('comparison-modal').style.display = 'flex';
                document.body.style.overflow = 'hidden';
            };
        }

        // Sector Peers Button Handler
        const sectorBtn = document.getElementById('sector-peers-btn');
        if (sectorBtn) {
            sectorBtn.onclick = async () => {
                if (window.isFetchingSectorPeers) return;
                window.isFetchingSectorPeers = true;

                sectorBtn.disabled = true;
                sectorBtn.textContent = 'Loading...';
                errSpan.style.display = 'none';

                try {
                    const targetTicker = (prof.ticker || currentTicker || '').toUpperCase();
                    const res = await fetch(`/api/sector-peers/${encodeURIComponent(targetTicker)}?t=${Date.now()}`);
                    if (!res.ok) throw new Error('Failed to fetch sector peers');
                    const sectorPeers = await res.json();

                    if (!sectorPeers || sectorPeers.length === 0) {
                        throw new Error('No sector peers found');
                    }

                    // Deduplicate against existing peers and target company using base tickers (e.g. GOOG vs GOOGL)
                    const getBaseTicker = (t) => {
                        t = (t || '').toUpperCase();
                        if (t.startsWith('GOOG')) return 'GOOG';
                        if (t.startsWith('BRK')) return 'BRK';
                        if (t.startsWith('RDS')) return 'RDS';
                        return t.split('.')[0].split('-')[0].replace(/L$/, '');
                    };

                    const existingBases = new Set(
                        (prof.competitor_metrics || []).map(p => getBaseTicker(p.ticker))
                    );
                    existingBases.add(getBaseTicker(targetTicker));

                    let addedCount = 0;
                    for (const sp of sectorPeers) {
                        const spTicker = (sp.ticker || '').toUpperCase();
                        const spBase = getBaseTicker(spTicker);
                        if (!spTicker || existingBases.has(spBase)) continue;

                        existingBases.add(spBase);

                        // Build peer object with all required fields
                        const newPeer = {
                            ticker: spTicker,
                            name: sp.name || spTicker,
                            market_cap: sp.market_cap,
                            pe_ratio: sp.forward_pe || sp.pe_ratio,
                            forward_pe: sp.forward_pe,
                            fwd_pe: sp.forward_pe,
                            peg_ratio: sp.peg_ratio,
                            eps: sp.eps,
                            forward_eps: sp.forward_eps,
                            fwd_eps: sp.forward_eps,
                            ps_ratio: sp.ps_ratio,
                            fwd_ps: sp.forward_ev_sales || sp.ps_ratio,
                            forward_ev_sales: sp.forward_ev_sales,
                            price_to_book: sp.price_to_book,
                            ev_to_ebitda: sp.forward_ev_ebitda || sp.ev_to_ebitda,
                            forward_ev_ebitda: sp.forward_ev_ebitda,
                            revenue: sp.revenue,
                            forward_revenue: sp.forward_revenue,
                            pfcf_ratio: sp.pfcf_ratio,
                            fcf: sp.fcf,
                            operating_margin: sp.operating_margin,
                            margin: sp.operating_margin,
                            earnings_growth: sp.earnings_growth,
                            eps_growth: sp.earnings_growth,
                            revenue_growth: sp.revenue_growth,
                            rev_growth: sp.revenue_growth,
                            price: sp.price,
                            avg_2y_eps_growth: sp.avg_2y_eps_growth,
                            forward_peg: sp.forward_peg,
                            forward_pe_custom: sp.forward_pe_custom,
                            cagr_5y_custom: sp.cagr_5y_custom,
                            peg_custom: sp.peg_custom,
                            ps_forward_custom: sp.ps_forward_custom,
                            fcf_margin_custom: sp.fcf_margin_custom,
                            pfcf_forward_custom: sp.pfcf_forward_custom
                        };

                        if (!prof.competitor_metrics) prof.competitor_metrics = [];
                        prof.competitor_metrics.push(newPeer);
                        addedCount++;
                    }

                    // Calculate and cache Sector Median PEG from fresh API response
                    const freshValidPegs = sectorPeers
                        .filter(sp => (sp.ticker || '').toUpperCase() !== targetTicker)
                        .map(sp => {
                            const price = parseFloat(sp.price || sp.current_price);
                            let eps = parseFloat(sp.adjusted_eps);
                            if (isNaN(eps) || eps <= 0) eps = parseFloat(sp.eps);

                            const cagr2y = parseFloat(sp.avg_2y_eps_growth || sp.earnings_growth);

                            if (!isNaN(price) && price > 0 && !isNaN(eps) && eps > 0 && !isNaN(cagr2y) && cagr2y > 0) {
                                const peNonGaap = price / eps;
                                return peNonGaap / (cagr2y * 100);
                            }
                            return null;
                        })
                        .filter(v => v !== null);

                    if (freshValidPegs.length > 0 && prof.sector) {
                        freshValidPegs.sort((a, b) => a - b);
                        const mid = Math.floor(freshValidPegs.length / 2);
                        const sectorMedian = freshValidPegs.length % 2 === 0 ? (freshValidPegs[mid - 1] + freshValidPegs[mid]) / 2 : freshValidPegs[mid];
                        localStorage.setItem('sectorMedianPeg_' + prof.sector, sectorMedian);
                    }

                    if (addedCount === 0) {
                        errSpan.textContent = 'All sector peers already in comparison, but Sector Median PEG was refreshed!';
                        errSpan.style.display = 'inline';
                    }

                    // Update competitors list
                    prof.competitors = prof.competitor_metrics.map(p => p.ticker);

                    // Persist
                    localStorage.setItem('customPeers_' + (prof.ticker || currentTicker), JSON.stringify(prof.competitor_metrics));

                    // Recalculate
                    recalcIndustryPeg(prof);
                    updateFairValue();
                    saveOverridesDebounced(currentTicker);

                    // Re-render (silent to preserve DCF inputs)
                    renderComparisonModal(prof);
                    displayData(globalData, true);
                    document.getElementById('comparison-modal').style.display = 'flex';
                    document.body.style.overflow = 'hidden';

                } catch (e) {
                    errSpan.textContent = e.message;
                    errSpan.style.display = 'inline';
                } finally {
                    window.isFetchingSectorPeers = false;
                    const btn = document.getElementById('sector-peers-btn');
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = '🏢 Sector';
                    }
                }
            };
        }
        if (addBtn && addInput) {
            addBtn.onclick = async () => {
                const rawVal = addInput.value.trim().toUpperCase();
                if (!rawVal) return;
                if (window.isFetchingPeer) return;

                window.isFetchingPeer = true;
                window.fetchingPeerTicker = rawVal;

                errSpan.style.display = 'none';
                addBtn.disabled = true;
                addBtn.textContent = 'Fetching...';

                try {
                    const res = await fetch(`/api/valuation/${encodeURIComponent(rawVal)}?t=${Date.now()}&skip_peers=true`);
                    if (!res.ok) {
                        let detail = 'Ticker not found or valuation missing';
                        try { const errJson = await res.json(); detail = errJson.detail || detail; } catch (_) { }
                        throw new Error(detail);
                    }
                    const peerData = await res.json();

                    const peerProf = peerData.company_profile;
                    if (!peerProf) throw new Error('Invalid peer metrics received');
                    peerProf.ticker = peerProf.ticker || peerData.ticker || rawVal;

                    const exists = (prof.competitor_metrics || []).some(p => p.ticker.toUpperCase() === rawVal);
                    if (exists) throw new Error('Peer is already in comparison');

                    const mainFcf = peerData.formula_data?.dcf?.fcf || peerProf.fcf;
                    const pfcf = peerProf.pfcf_ratio;

                    const newPeerObj = {
                        ticker: peerProf.ticker.toUpperCase(),
                        name: peerProf.name || 'Competitor',
                        market_cap: peerProf.market_cap,
                        pe_ratio: peerProf.fwd_eps > 0 ? (peerData.current_price / peerProf.fwd_eps) : peerProf.trailing_pe,
                        fwd_pe: peerProf.fwd_eps > 0 ? (peerData.current_price / peerProf.fwd_eps) : null,
                        forward_pe: peerProf.forward_pe || (peerProf.fwd_eps > 0 ? (peerData.current_price / peerProf.fwd_eps) : null),
                        peg_ratio: peerProf.peg_ratio,
                        trailing_eps: peerProf.trailing_eps,
                        eps: peerProf.trailing_eps,
                        fwd_eps: peerProf.fwd_eps,
                        ps_ratio: peerProf.ps_ratio,
                        fwd_ps: peerProf.fwd_ps,
                        forward_ev_sales: peerProf.forward_ev_sales || peerProf.fwd_ps,
                        price_to_book: peerProf.price_to_book,
                        ev_to_ebitda: peerData.formula_data?.relative?.company_ev_ebitda || peerProf.ev_to_ebitda,
                        forward_ev_ebitda: peerProf.forward_ev_ebitda || peerData.formula_data?.relative?.company_ev_ebitda || peerProf.ev_to_ebitda,
                        revenue: peerData.revenue || peerProf.revenue,
                        pfcf_ratio: pfcf,
                        fcf: mainFcf,
                        margin: peerProf.operating_margin,
                        operating_margin: peerProf.operating_margin,
                        eps_growth: peerProf.earnings_growth,
                        rev_growth: peerProf.revenue_growth,
                        earnings_growth: peerProf.earnings_growth,
                        revenue_growth: peerProf.revenue_growth,
                        forward_revenue: peerProf.forward_revenue,
                        forward_pe_custom: peerProf.forward_pe_custom || (peerProf.fwd_eps > 0 ? (peerData.current_price / peerProf.fwd_eps) : null),
                        cagr_5y_custom: peerProf.cagr_5y_custom,
                        peg_custom: peerProf.peg_custom || peerProf.peg_ratio,
                        ps_forward_custom: peerProf.ps_forward_custom,
                        fcf_margin_custom: peerProf.fcf_margin_custom,
                        pfcf_forward_custom: peerProf.pfcf_forward_custom
                    };

                    if (!prof.competitor_metrics) prof.competitor_metrics = [];
                    prof.competitor_metrics.push(newPeerObj);

                    if (!prof.competitors) prof.competitors = [];
                    if (!prof.competitors.includes(rawVal)) prof.competitors.push(rawVal);

                    recalcIndustryPeg(prof);

                    // Persist to local storage
                    localStorage.setItem('customPeers_' + (prof.ticker || currentTicker), JSON.stringify(prof.competitor_metrics));

                    // Update calculations and UI
                    updateFairValue();

                    window.isFetchingPeer = false;
                    window.fetchingPeerTicker = '';

                    renderComparisonModal(prof);

                    if (typeof window._renderProfile === 'function') {
                        window._renderProfile();
                    }
                } catch (e) {
                    errSpan.textContent = e.message;
                    errSpan.style.display = 'inline';
                } finally {
                    window.isFetchingPeer = false;
                    window.fetchingPeerTicker = '';
                    const currentAddBtn = document.getElementById('add-peer-btn');
                    if (currentAddBtn) {
                        currentAddBtn.disabled = false;
                        currentAddBtn.textContent = 'Add';
                    }
                    const currentAddInput = document.getElementById('add-peer-input');
                    if (currentAddInput) {
                        currentAddInput.value = '';
                    }
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
                statusElem.textContent = "null";
                statusElem.style.color = "var(--text-muted)";
            }
            if (valueElem) valueElem.textContent = "null";
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

    // ── Beneish M-Score UI ────────────────────────────────────────────────────
    const updateBeneishUI = (beneishData) => {
        const circle = document.getElementById('beneish-score-circle');
        const fill = document.getElementById('beneish-score-fill');
        const badge = document.getElementById('beneish-label-badge');
        if (!circle || !fill) return;

        circle.className = 'score-circle';
        fill.className = 'score-bar-fill';
        circle.style.color = '';
        fill.style.backgroundColor = '';
        fill.style.width = '0%';

        if (!beneishData || beneishData.m_score == null) {
            circle.textContent = 'N/A';
            circle.style.color = 'var(--text-muted)';
            fill.style.backgroundColor = 'var(--text-muted)';
            if (badge) { badge.textContent = '--'; badge.style.background = 'rgba(148,163,184,0.2)'; badge.style.color = 'var(--text-muted)'; }
            return;
        }

        const scoreVal = beneishData.m_score;
        circle.textContent = scoreVal;

        // Bar logic for Beneish. Let's map -4.00 to 100% safe, and 0.00 to 0%
        let barPct = Math.round(((scoreVal - 0) / (-4.0 - 0)) * 100);
        if (barPct < 0) barPct = 0;
        if (barPct > 100) barPct = 100;

        setTimeout(() => { fill.style.width = `${barPct}%`; }, 50);

        if (beneishData.status === 'pass') {
            circle.classList.add('score-green');
            fill.classList.add('bg-score-green');
            if (badge) { badge.textContent = 'Safe'; badge.style.background = 'rgba(16,185,129,0.25)'; badge.style.color = 'var(--accent)'; }
        } else if (beneishData.status === 'fail') {
            circle.classList.add('score-red');
            fill.classList.add('bg-score-red');
            if (badge) { badge.textContent = 'Risk'; badge.style.background = 'rgba(239,68,68,0.2)'; badge.style.color = 'var(--danger)'; }
        } else {
            circle.style.color = 'var(--text-muted)';
            fill.style.backgroundColor = 'var(--text-muted)';
            if (badge) { badge.textContent = '--'; badge.style.background = 'rgba(148,163,184,0.2)'; badge.style.color = 'var(--text-muted)'; }
        }
    };

    // ── Piotroski F-Score UI ──────────────────────────────────────────────────
    const updatePiotroskiUI = (scoreVal) => {
        const circle = document.getElementById('piotroski-score-circle');
        const fill = document.getElementById('piotroski-score-fill');
        const badge = document.getElementById('piotroski-label-badge');
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
        const fill = document.getElementById('rule40-score-fill');
        if (!circle || !fill) return;

        // Reset
        circle.className = 'score-circle';
        fill.className = 'score-bar-fill';
        circle.style.color = '';
        fill.style.backgroundColor = '';
        fill.style.width = '0%';
        circle.style.width = '';
        circle.style.padding = '0';
        circle.style.borderRadius = '';

        // Adjust parent grid to accommodate wider percentage text
        const parentDisplay = circle.parentElement;
        if (parentDisplay && parentDisplay.classList.contains('score-display')) {
            parentDisplay.style.gridTemplateColumns = 'min-content 1fr 2.5rem';
            circle.style.marginRight = '0.5rem';
        }

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
        const bodyEl = document.getElementById('score-modal-body-content');
        if (!modalEl || !bodyEl) return;

        if (!rule40Data || rule40Data.total === null) {
            bodyEl.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 2rem;">No Rule of 40 data available.</p>`;
            modalEl.style.display = 'flex';
            return;
        }

        const total = rule40Data.total;
        const labelColor = rule40Data.passed ? 'var(--accent)' : (total > 30 ? '#fbbf24' : 'var(--danger)');
        const labelText = rule40Data.label || (rule40Data.passed ? 'Strong' : (total > 30 ? 'Moderate' : 'Weak'));

        let html = `
            <div style="text-align:center; margin-bottom: 1.5rem; padding-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.1);">
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
                
                <div style="display:grid; grid-template-columns: 1fr max-content 20px; align-items:center; padding:10px 0; gap:12px 16px;">
                    <!-- Revenue Growth Row -->
                    <div style="font-weight:600; font-size:clamp(0.75rem, 3vw, 0.88rem); color:white; line-height:1.2; white-space:nowrap;" title="${rule40Data.rev_growth_label || 'Revenue Growth'}">${rule40Data.rev_growth_label || 'Revenue Growth'}</div>
                    <div style="font-weight:700; font-size:clamp(0.8rem, 3vw, 0.9rem); color:rgba(255,255,255,0.85); font-family:monospace; text-align:right;">
                        ${(rule40Data.revenue_growth || 0).toFixed(1)} <span style="font-size: 0.8em; color: rgba(255,255,255,0.7);">%</span>
                    </div>
                    <div style="display:flex; justify-content:center;">
                        <span style="width:8px; height:8px; border-radius:50%; background:${(rule40Data.revenue_growth || 0) > 0 ? 'var(--accent)' : 'var(--danger)'}; display:inline-block;"></span>
                    </div>

                    <!-- Full-width divider -->
                    <div style="grid-column: 1 / -1; height: 1px; background: rgba(255,255,255,0.05); margin: 2px 0;"></div>

                    <!-- FCF Margin Row -->
                    <div style="font-weight:600; font-size:clamp(0.75rem, 3vw, 0.88rem); color:white; line-height:1.2; white-space:nowrap;" title="${rule40Data.margin_label || 'FCF Margin'}">${rule40Data.margin_label || 'FCF Margin'}</div>
                    <div style="font-weight:700; font-size:clamp(0.8rem, 3vw, 0.9rem); color:rgba(255,255,255,0.85); font-family:monospace; text-align:right;">
                        ${(rule40Data.fcf_margin || 0).toFixed(1)} <span style="font-size: 0.8em; color: rgba(255,255,255,0.7);">%</span>
                    </div>
                    <div style="display:flex; justify-content:center;">
                        <span style="width:8px; height:8px; border-radius:50%; background:${(rule40Data.fcf_margin || 0) > 0 ? 'var(--accent)' : 'var(--danger)'}; display:inline-block;"></span>
                    </div>
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
        const getDynamicEpsGrowth = () => {
            if (window._customScenariosData && window._customScenariosData[_currentScenario] && window._customScenariosData[_currentScenario].eps !== null) {
                return window._customScenariosData[_currentScenario].eps / 100;
            }
            if (globalData && globalData.computed_eps_growth != null && !isNaN(globalData.computed_eps_growth)) {
                return globalData.computed_eps_growth;
            }
            let epsFallback = currentFormulaData?.peg?.eps_growth_estimated || globalData?.company_profile?.earnings_growth || 0.05;
            if (_currentScenario === 'bear') return epsFallback * 0.70;
            if (_currentScenario === 'bull') return epsFallback * 1.30;
            return epsFallback;
        };

        const getDynamicRevGrowth = () => {
            if (window._customScenariosData && window._customScenariosData[_currentScenario] && window._customScenariosData[_currentScenario].rev13 !== null) {
                return window._customScenariosData[_currentScenario].rev13 / 100;
            }
            if (globalData && globalData.computed_dcf_growth != null && !isNaN(globalData.computed_dcf_growth)) {
                return globalData.computed_dcf_growth;
            }
            let revFallback = globalData?.company_profile?.revenue_growth || 0.08;
            if (_currentScenario === 'bear') return revFallback * 0.70;
            if (_currentScenario === 'bull') return revFallback * 1.30;
            return revFallback;
        };

        window._getDynamicEpsGrowth = getDynamicEpsGrowth;
        window._getDynamicRevGrowth = getDynamicRevGrowth;

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

            let rawBuybackRate = 0;
            let rawSbcRate = 0;

            if (buybackSrc === 'historical') {
                rawBuybackRate = currentFormulaData.dcf.historic_buyback_rate || 0;
            } else if (buybackSrc === 'custom') {
                const rawVal = document.getElementById('dcf-custom-buyback').value;
                rawBuybackRate = (rawVal === '' || isNaN(parseLocaleFloat(rawVal))) ? 0 : parseLocaleFloat(rawVal) / 100;

                const sbcVal = document.getElementById('dcf-custom-sbc').value;
                rawSbcRate = (sbcVal === '' || isNaN(parseLocaleFloat(sbcVal))) ? 0 : parseLocaleFloat(sbcVal) / 100;
            }

            let buybackRate = rawBuybackRate - rawSbcRate;

            let baseFcf = currentFormulaData.dcf.fcf;
            let baseRevenue = globalData.revenue;

            // Align base FCF and Revenue with the latest historical year (e.g. 2025 Base)
            if (globalData.historical_data && globalData.historical_data.years) {
                const histFcf = globalData.historical_data.fcf;
                const histRev = globalData.historical_data.revenue;
                const years = globalData.historical_data.years;

                let lastActualIdx = -1;
                for (let i = years.length - 1; i >= 0; i--) {
                    if (!String(years[i]).includes('Est')) {
                        lastActualIdx = i;
                        break;
                    }
                }

                if (lastActualIdx >= 0) {
                    if (histFcf && histFcf.length > lastActualIdx && histFcf[lastActualIdx] != null) {
                        baseFcf = histFcf[lastActualIdx];
                    }
                    if (histRev && histRev.length > lastActualIdx && histRev[lastActualIdx] != null) {
                        baseRevenue = histRev[lastActualIdx];
                    }
                }
            }

            baseRevenue = baseRevenue || (prof.market_cap && prof.ps_ratio && prof.ps_ratio > 0 ? prof.market_cap / prof.ps_ratio : null) || 0;

            const customMarginEl = document.getElementById('dcf-custom-fcf-margin');
            let cs = window._customScenariosData && window._customScenariosData[_currentScenario] ? window._customScenariosData[_currentScenario] : null;
            let customMargin = (customMarginEl && customMarginEl.value !== '') ? parseLocaleFloat(customMarginEl.value) : null;
            if (cs && cs.fcfMargin !== null) {
                customMargin = cs.fcfMargin;
            }

            const customMarginGrowthEl = document.getElementById('dcf-custom-margin-growth');
            const customMarginGrowth = (customMarginGrowthEl && customMarginGrowthEl.value !== '') ? parseLocaleFloat(customMarginGrowthEl.value) / 100 : 0.002;

            const fcfParam = { fcf: baseFcf, revenue: baseRevenue, customMargin: customMargin, marginGrowth: customMarginGrowth };

            const shares = prof.shares_outstanding;

            // Dynamic WACC and Perpetual Growth from backend
            const w = currentFormulaData.dcf.discount_rate || 0.09;
            const p = currentFormulaData.dcf.perpetual_growth || 0.02;

            if (fcfSource === 'revenue' || fcfSource === 'eps_growth') {
                const waccInput = document.getElementById('dcf-custom-wacc');
                let wAnalyst = (waccInput && waccInput.value) ? parseLocaleFloat(waccInput.value) / 100 : w;
                if (cs && cs.wacc !== null) wAnalyst = cs.wacc / 100;

                const pRaw = document.getElementById('dcf-custom-perp')?.value;
                let pCustom = (pRaw === '' || isNaN(parseLocaleFloat(pRaw))) ? p : parseLocaleFloat(pRaw) / 100;
                if (cs && cs.perp !== null) pCustom = cs.perp / 100;

                let em = parseLocaleFloat(document.getElementById('input-exit-multiple')?.value) || (globalData.dcf_assumptions?.recommended_exit_multiple || 15.0);
                if (cs && cs.exit !== null) em = cs.exit;

                let g;
                if (fcfSource === 'revenue') {
                    const revBase = getDynamicRevGrowth();
                    const g13 = Math.min(Math.round(revBase * 1000) / 1000, 0.50);

                    const g46 = Math.min(revBase * 0.75, 0.30);

                    const g78 = Math.min(revBase * 0.50, 0.15);
                    const g910 = Math.min(revBase * 0.25, 0.05);
                    g = [];
                    for (let y = 1; y <= 10; y++) {
                        if (y <= 3) g.push(g13);
                        else if (y <= 6) g.push(g46);
                        else if (y <= 8) g.push(g78);
                        else g.push(g910);
                    }
                } else {
                    const epsBase = getDynamicEpsGrowth();
                    const epsG13 = Math.min(Math.round(epsBase * 1000) / 1000, 0.50);
                    const epsG46 = Math.min(epsBase * 0.75, 0.30);
                    const epsG78 = Math.min(epsBase * 0.50, 0.15);
                    const epsG910 = Math.min(epsBase * 0.25, 0.05);
                    g = [];
                    for (let y = 1; y <= 10; y++) {
                        if (y <= 3) g.push(epsG13);
                        else if (y <= 6) g.push(epsG46);
                        else if (y <= 8) g.push(epsG78);
                        else g.push(epsG910);
                    }
                }

                if (currentFormulaData.dcf) currentFormulaData.dcf.eps_growth_applied = g;

                dcfValObj = calcLocalDcf(fcfParam, g, wAnalyst, pCustom, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years, em, _realApiPrice);
            }
            else if (fcfSource === 'historical') {
                const histBase = (prof.historic_fcf_growth != null ? prof.historic_fcf_growth : 0.05);
                const hg13 = Math.min(Math.round(histBase * 1000) / 1000, 0.50);
                const hg46 = Math.min(histBase * 0.75, 0.30);
                const hg78 = Math.min(histBase * 0.50, 0.15);
                const hg910 = Math.min(histBase * 0.25, 0.05);
                const hgArray = [];
                for (let y = 1; y <= 10; y++) {
                    if (y <= 3) hgArray.push(hg13);
                    else if (y <= 6) hgArray.push(hg46);
                    else if (y <= 8) hgArray.push(hg78);
                    else hgArray.push(hg910);
                }
                if (currentFormulaData.dcf) currentFormulaData.dcf.eps_growth_applied = hgArray;
                const em = parseLocaleFloat(document.getElementById('input-exit-multiple')?.value) || (globalData.dcf_assumptions?.recommended_exit_multiple || 10.0);
                dcfValObj = calcLocalDcf(fcfParam, hgArray, w, p, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years, em, _realApiPrice);
            } else if (fcfSource === 'custom') {
                // v290: Force-sync growth inputs to current scenario before reading
                const scenarioGrowth = window.getDcfGrowthDefault(globalData);
                const g13Input = document.getElementById('dcf-growth-1-3');
                if (g13Input) {
                    const sg = Math.min(scenarioGrowth, 50);
                    if (g13Input.dataset.isDefault === 'true' || !g13Input.value || g13Input.value === '') {
                        g13Input.value = formatCleanInputVal(sg);
                    }
                    // Also cascade to dependent fields
                    const g46Input = document.getElementById('dcf-growth-4-6');
                    const g78Input = document.getElementById('dcf-growth-7-8');
                    const g910Input = document.getElementById('dcf-growth-9-10');
                    if (g46Input && (g46Input.dataset.isDefault === 'true' || !g46Input.value || g46Input.value === '')) g46Input.value = formatCleanInputVal(Math.min(sg * 0.75, 30));
                    if (g78Input && (g78Input.dataset.isDefault === 'true' || !g78Input.value || g78Input.value === '')) g78Input.value = formatCleanInputVal(Math.min(sg * 0.50, 15));
                    if (g910Input && (g910Input.dataset.isDefault === 'true' || !g910Input.value || g910Input.value === '')) g910Input.value = formatCleanInputVal(Math.min(sg * 0.25, 5));
                }

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
                    let g13 = v13 / 100;
                    let g46 = v46 / 100;
                    let g78 = (v78 ?? 0) / 100;
                    let g910 = (v910 ?? 0) / 100;

                    // Override all growths if custom scenario provides 1-3Y growth
                    if (window._customScenariosData && window._customScenariosData[_currentScenario] && window._customScenariosData[_currentScenario].rev13 !== null) {
                        const baseRev = window._customScenariosData[_currentScenario].rev13 / 100;
                        g13 = Math.min(Math.round(baseRev * 1000) / 1000, 0.50);
                        g46 = Math.min(baseRev * 0.75, 0.30);
                        g78 = Math.min(baseRev * 0.50, 0.15);
                        g910 = Math.min(baseRev * 0.25, 0.05);
                    }

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

                    let csWacc = (cs && cs.wacc !== null) ? cs.wacc / 100 : null;
                    let csPerp = (cs && cs.perp !== null) ? cs.perp / 100 : null;
                    let csExit = (cs && cs.exit !== null) ? cs.exit : null;

                    const wCustom = csWacc !== null ? csWacc : ((wRaw === '' || isNaN(parseLocaleFloat(wRaw))) ? 0.09 : parseLocaleFloat(wRaw) / 100);
                    const pCustom = csPerp !== null ? csPerp : ((pRaw === '' || isNaN(parseLocaleFloat(pRaw))) ? 0.025 : parseLocaleFloat(pRaw) / 100);
                    const em = csExit !== null ? csExit : ((emRaw === '' || isNaN(parseLocaleFloat(emRaw))) ? (globalData.dcf_assumptions?.recommended_exit_multiple || 10.0) : parseLocaleFloat(emRaw));

                    dcfValObj = calcLocalDcf(fcfParam, growthArr, wCustom, pCustom, shares, currentFormulaData.dcf.total_cash, currentFormulaData.dcf.total_debt, buybackRate, years, em, _realApiPrice);
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
            let strictCagrMode = false;
            let fwdPe = null;

            if (pegSrc === 'analyst') {
                strictCagrMode = true;
                usedGrowth = null; // Default to null for strict 2-Year CAGR
                if (window._customScenariosData && window._customScenariosData[_currentScenario] && window._customScenariosData[_currentScenario].eps !== null) {
                    usedGrowth = window._customScenariosData[_currentScenario].eps / 100;
                    strictCagrMode = false; // We have custom growth, not strict CAGR
                }
                const pegEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
                if (pegEsts && pegEsts.length >= 2) {
                    const reportedE = globalData.eps_estimates?.find(e => e && e.status === 'reported');
                    const baseEps = reportedE ? reportedE.avg : (globalData.company_profile.adjusted_eps || globalData.company_profile.trailing_eps || 0);
                    if (baseEps > 0) {
                        let y1, y2;
                        if (_currentScenario === 'bear') { y1 = pegEsts[0].low ?? pegEsts[0].avg; y2 = pegEsts[1].low ?? pegEsts[1].avg; }
                        else if (_currentScenario === 'bull') { y1 = pegEsts[0].high ?? pegEsts[0].avg; y2 = pegEsts[1].high ?? pegEsts[1].avg; }
                        else { y1 = pegEsts[0].avg; y2 = pegEsts[1].avg; }

                        if (usedGrowth === null) {
                            if (globalData.computed_eps_growth != null && !isNaN(globalData.computed_eps_growth)) {
                                usedGrowth = globalData.computed_eps_growth;
                            } else {
                                if (baseEps > 0 && y2 > 0) {
                                    usedGrowth = Math.pow(y2 / baseEps, 0.5) - 1;
                                } else {
                                    const g1 = (y1 / baseEps) - 1;
                                    const g2 = (y2 / y1) - 1;
                                    usedGrowth = (g1 + g2) / 2.0;
                                }
                            }
                        }

                        // Fwd P/E is based on FY1
                        fwdPe = (y1 > 0) ? (_realApiPrice / y1) : null;
                    }
                }
            } else if (pegSrc === '5ycagr') {
                usedGrowth = globalData.company_profile.cagr_5y_custom || currentFormulaData.peg.eps_growth_5y_cagr || usedGrowth;
                if (window._customScenariosData && window._customScenariosData[_currentScenario] && window._customScenariosData[_currentScenario].eps !== null) {
                    usedGrowth = window._customScenariosData[_currentScenario].eps / 100;
                }
                fwdPe = globalData.company_profile.forward_pe_custom || currentFormulaData.peg.fwd_pe || null;
            } else if (pegSrc === 'custom') {
                const rawG = document.getElementById('peg-custom-growth').value;
                usedGrowth = (rawG === '' || isNaN(parseFloat(rawG))) ? 0.20 : parseFloat(rawG) / 100;
                fwdPe = globalData.company_profile.forward_pe_custom || currentFormulaData.peg.fwd_pe || null;
            }

            let eps = globalData.company_profile.adjusted_eps || globalData.company_profile.trailing_eps || 0;
            const currentPe = fwdPe !== null ? fwdPe : (eps > 0 ? (_realApiPrice / eps) : (currentFormulaData.peg.current_pe || parseFloat(globalData.company_profile.current_pe) || parseFloat(globalData.company_profile.trailing_pe) || 0));

            const pegMode = document.getElementById('peg-mode')?.value || 'standard';
            const sector = globalData.company_profile.sector || "";
            const industry = globalData.company_profile.industry || "";
            const isTelecom = industry.toLowerCase().includes("telecom");

            // Sector Median Logic for PEG
            const cachedSectorPeg = localStorage.getItem('sectorMedianPeg_' + sector);

            // Calculate median of peg_custom from peers
            let medianPegCustom = null;
            if (globalData.company_profile && globalData.company_profile.competitor_metrics && globalData.company_profile.competitor_metrics.length > 0) {
                const validPegs = globalData.company_profile.competitor_metrics
                    .map(p => parseFloat(p.peg_custom))
                    .filter(val => !isNaN(val) && val > 0)
                    .sort((a, b) => a - b);

                if (validPegs.length > 0) {
                    const mid = Math.floor(validPegs.length / 2);
                    medianPegCustom = validPegs.length % 2 !== 0 ? validPegs[mid] : (validPegs[mid - 1] + validPegs[mid]) / 2;
                }
            }

            // Prioritize dynamically calculated median from custom peers over cached global sector median
            const industryPegRaw = medianPegCustom != null ? medianPegCustom : ((currentFormulaData.peg && currentFormulaData.peg.industry_peg != null)
                ? currentFormulaData.peg.industry_peg
                : (cachedSectorPeg ? parseFloat(cachedSectorPeg) : 1.0));

            let targetPeg = 1.0;
            if (pegMode === 'industry') {
                targetPeg = industryPegRaw;
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

            if (strictCagrMode && (usedGrowth === null || usedGrowth <= 0 || currentPe <= 0)) {
                // If strict mode and missing data, fail PEG
                pegVal = null;
                currentPegToDisplay = null;
                pegMos = null;
            } else if (usedGrowth > 0 && currentPe > 0 && targetPeg > 0) {
                const originalPeg = currentPe / (usedGrowth * 100);
                pegVal = _realApiPrice * (targetPeg / originalPeg);

                const simPe = fwdPe !== null ? fwdPe * (globalData.current_price / _realApiPrice) : (eps > 0 ? (globalData.current_price / eps) : (currentPe * (globalData.current_price / _realApiPrice)));
                currentPegToDisplay = simPe / (usedGrowth * 100);

                if (pegVal != null) {
                    pegMos = ((pegVal - globalData.current_price) / globalData.current_price) * 100;
                }

                currentFormulaData.peg.dynamic_growth = usedGrowth;
                currentFormulaData.peg.dynamic_fv = pegVal;
                currentFormulaData.peg.dynamic_peg = currentPegToDisplay;
                currentFormulaData.peg.dynamic_pe = simPe;
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
            
            // Prefer dynamically calculated sector median based on current peers in table
            let industryPeg = null;
            if (globalData && globalData.company_profile) {
                industryPeg = recalcIndustryPeg(globalData.company_profile);
            }
            if (industryPeg == null && currentFormulaData.peg) {
                industryPeg = currentFormulaData.peg.industry_peg || currentFormulaData.peg.sector_median_peg;
            }
            
            if (pegVal != null && currentPegToDisplay != null) {
                const sector = globalData.company_profile.sector || "";
                const industry = globalData.company_profile.industry || "";
                const isTelecom = industry.toLowerCase().includes("telecom");

                let targetPeg = 1.0;
                if (pegMode === 'industry') {
                    targetPeg = industryPeg;
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
                
                if (displayCurrent != null && displayTarget != null) {
                    pegCompareElem.textContent = `PEG = ${displayCurrent.toFixed(2)} vs PEG ${pegMode === 'industry' ? 'Sector' : 'Std'} = ${displayTarget.toFixed(2)}`;
                } else {
                    pegCompareElem.textContent = `PEG = N/A vs PEG ${pegMode === 'industry' ? 'Sector' : 'Std'} = N/A`;
                }

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

            if (epsSource === 'analyst') {
                usedGrowth = getDynamicEpsGrowth();
            } else if (epsSource === '5ycagr') {
                usedGrowth = globalData.company_profile.cagr_5y_custom || pl.eps_growth_5y_cagr || usedGrowth;
                if (window._customScenariosData && window._customScenariosData[_currentScenario] && window._customScenariosData[_currentScenario].eps !== null) {
                    usedGrowth = window._customScenariosData[_currentScenario].eps / 100;
                }
            } else if (epsSource === 'historical') {
                usedGrowth = prof.historic_eps_growth != null ? prof.historic_eps_growth : 0.05;
            } else if (epsSource === 'custom') {
                const rawG = document.getElementById('lynch-custom-growth').value;
                usedGrowth = (rawG === '' || isNaN(parseFloat(rawG))) ? 0.20 : parseFloat(rawG) / 100;
            }
            let targetEps = baseEps;
            for (let i = 0; i < 3; i++) {
                if (targetEps < 0) {
                    targetEps = targetEps + Math.abs(targetEps) * usedGrowth;
                } else {
                    targetEps *= (1 + usedGrowth);
                }
            }

            const multEl = document.getElementById('lynch-multiple-source');
            const multVal = multEl ? multEl.value : 'system';
            const multCustomInputs = document.getElementById('lynch-custom-multiple-inputs');
            if (multCustomInputs) multCustomInputs.style.display = multVal === 'custom' ? 'grid' : 'none';

            let selectedMult = 20;
            if (multVal === 'system') {
                let g = usedGrowth * 100;
                if (g <= 0) {
                    selectedMult = 8.5;
                } else if (g <= 10) {
                    selectedMult = 8.5 + (g / 10) * 6.5;
                } else if (g <= 15) {
                    selectedMult = 15 + ((g - 10) / 5) * 5;
                } else if (g <= 20) {
                    selectedMult = 20 + ((g - 15) / 5) * 5;
                } else {
                    selectedMult = 25;
                }
            } else if (multVal === 'historical') {
                selectedMult = pl.historic_pe || 20;
            } else if (multVal === 'custom') {
                selectedMult = parseFloat(document.getElementById('lynch-custom-mult').value) || 18;
            } else {
                // Fallback just in case
                selectedMult = 20;
            }
            let csLynch = window._customScenariosData && window._customScenariosData[_currentScenario] ? window._customScenariosData[_currentScenario] : null;
            if (csLynch && csLynch.pe !== null) {
                selectedMult = csLynch.pe;
            }

            if (multVal === 'historical' && (!csLynch || csLynch.pe === null)) {
                if (_currentScenario === 'bear') selectedMult -= 3;
                else if (_currentScenario === 'bull') selectedMult += 3;
            }

            // New Return Rate Logic
            const returnRateEl = document.getElementById('lynch-return-rate');
            const returnRateVal = returnRateEl ? returnRateEl.value : '15';
            const returnCustomInputs = document.getElementById('lynch-custom-return-inputs');
            if (returnCustomInputs) returnCustomInputs.style.display = returnRateVal === 'custom' ? 'grid' : 'none';

            let discountRate = 0.15;
            if (returnRateVal === 'custom') {
                const rawR = document.getElementById('lynch-custom-return').value;
                discountRate = (rawR === '' || isNaN(parseFloat(rawR))) ? 0.15 : parseFloat(rawR) / 100;
            } else {
                discountRate = parseFloat(returnRateVal) / 100;
            }

            if (targetEps != null && targetEps > 0) {
                const fwdPrice = targetEps * selectedMult;
                lynchVal = fwdPrice / Math.pow(1 + discountRate, 3);
                currentFormulaData.peter_lynch.dynamic_fwd_price = fwdPrice;
            }

            // Store dynamics for modal
            currentFormulaData.peter_lynch.dynamic_growth = usedGrowth;
            currentFormulaData.peter_lynch.dynamic_fwd_eps = targetEps;
            currentFormulaData.peter_lynch.dynamic_fv = lynchVal;
            currentFormulaData.peter_lynch.dynamic_mult = selectedMult;
            currentFormulaData.peter_lynch.dynamic_discount = discountRate;

            const lynchCompareEl = document.getElementById('lynch-compare');
            if (lynchCompareEl) {
                lynchCompareEl.textContent = `FAIR P/E: ${selectedMult.toFixed(1)}X`;
            }
        }

        setValuationStatus(lynchVal, globalData.current_price, 'lynch-status', 'lynch-fair-value');

        const lynchCardMos = document.getElementById('lynch-card-mos');
        if (lynchCardMos && lynchVal != null) {
            const lynchMos = ((lynchVal - globalData.current_price) / globalData.current_price) * 100;
            lynchCardMos.textContent = `MOS: ${formatPercent(lynchMos)}`;
            lynchCardMos.style.color = lynchMos > 0 ? 'var(--accent)' : '#ef4444';
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

            const revGrowth = prof.revenue_growth || 0;
            const earnGrowth = prof.earnings_growth || 0;
            const fcfGrowth = prof.historic_fcf_growth || 0;

            const company_shares = (globalData.company_profile && globalData.company_profile.shares_outstanding) || 1;
            let company_eps = (rel.company_fwd_eps || 0) > 0 ? rel.company_fwd_eps : (rel.company_eps || 0);
            const explicit_fwd_ps = globalData.company_profile && globalData.company_profile.fwd_ps;
            let company_sales_share = explicit_fwd_ps > 0 ? (_realApiPrice / explicit_fwd_ps) : (rel.company_sales_share || 0);

            const eEsts = globalData.eps_estimates?.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
            if (eEsts && eEsts.length >= 1) {
                if (_currentScenario === 'bear') {
                    company_eps = eEsts[0].low ?? eEsts[0].avg;
                } else if (_currentScenario === 'bull') {
                    company_eps = eEsts[0].high ?? eEsts[0].avg;
                } else {
                    company_eps = eEsts[0].avg;
                }
            }

            const rEsts = globalData.rev_estimates?.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
            if (rEsts && rEsts.length >= 1) {
                let avgRev = null;
                if (_currentScenario === 'bear') {
                    avgRev = rEsts[0].low ?? rEsts[0].avg;
                } else if (_currentScenario === 'bull') {
                    avgRev = rEsts[0].high ?? rEsts[0].avg;
                } else {
                    avgRev = rEsts[0].avg;
                }
                if (avgRev != null && company_shares > 0) company_sales_share = avgRev / company_shares;
            }
            rel.dynamic_company_eps = company_eps;
            rel.dynamic_company_sales_share = company_sales_share;

            // v307c: Compute scenario-aware growth inline (not from stale computed_eps_growth)
            let dynEpsG = (prof.earnings_growth || 0);
            if (eEsts && eEsts.length >= 1) {
                // Growth = FY1 growth, scenario-aware
                const reported = globalData.eps_estimates?.find(e => e && e.status === 'reported');
                const baseEps = reported ? reported.avg : (rel.company_fwd_eps || rel.company_eps || 0);
                if (baseEps > 0) {
                    const fy1Val = _currentScenario === 'bear' ? (eEsts[0].low ?? eEsts[0].avg) : (_currentScenario === 'bull' ? (eEsts[0].high ?? eEsts[0].avg) : eEsts[0].avg);
                    dynEpsG = (fy1Val / baseEps) - 1;
                }
            } else if (globalData && globalData.computed_eps_growth != null) {
                dynEpsG = globalData.computed_eps_growth;
            }

            let dynRevG = (prof.revenue_growth || 0);
            if (rEsts && rEsts.length >= 1) {
                const reportedR = globalData.rev_estimates?.find(e => e && e.status === 'reported');
                const baseRev = reportedR ? reportedR.avg : (globalData.revenue || 0);
                if (baseRev > 0) {
                    const rfy1 = _currentScenario === 'bear' ? (rEsts[0].low ?? rEsts[0].avg) : (_currentScenario === 'bull' ? (rEsts[0].high ?? rEsts[0].avg) : rEsts[0].avg);
                    dynRevG = (rfy1 / baseRev) - 1;
                }
            } else if (globalData && globalData.computed_dcf_growth != null) {
                dynRevG = globalData.computed_dcf_growth;
            }

            // Store scenario-aware growth for showModal to use
            rel.dynamic_eps_growth = dynEpsG;
            rel.dynamic_rev_growth = dynRevG;

            const company_fcf_share = (rel.company_fcf_share || 0) * (1 + dynEpsG);
            const company_book_share = rel.company_book_share || 0; // Book value remains TTM
            const company_ebitda = (globalData.ebitda || 0) * (1 + dynEpsG);
            const company_debt = globalData.total_debt || 0;
            const company_cash = globalData.total_cash || 0;

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
            let rev = company_sales_share * company_shares;
            if (!rev || rev === 0) {
                rev = (globalData.revenue || 0) * (1 + dynRevG);
            }
            const ev_sales = rev * bPS;
            fvPS = company_shares > 0 ? (ev_sales - company_debt + company_cash) / company_shares : 0;
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
                // Override weights with user's custom values completely
                weights = window._relCustomWeights;
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
            const LABEL = { PE: 'FWD P/E', PFCF: 'P/FCF', PS: 'FWD EV/Sales', PB: 'P/B', EV_EBITDA: 'FWD EV/EBITDA', P_FFO: 'FWD P/FFO', P_AFFO: 'FWD P/AFFO' };
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

        let dynFwdEpsTop = globalData.company_profile?.fwd_eps || 0;
        let dynFwdRevTop = globalData.company_profile?.forward_revenue || 0;
        if (globalData.eps_estimates) {
            const eEstsTop = globalData.eps_estimates.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
            if (eEstsTop.length >= 1) {
                if (_currentScenario === 'bear') dynFwdEpsTop = eEstsTop[0].low ?? eEstsTop[0].avg;
                else if (_currentScenario === 'bull') dynFwdEpsTop = eEstsTop[0].high ?? eEstsTop[0].avg;
                else dynFwdEpsTop = eEstsTop[0].avg;
            }
        }
        if (globalData.rev_estimates) {
            const rEstsTop = globalData.rev_estimates.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
            if (rEstsTop.length >= 1) {
                if (_currentScenario === 'bear') dynFwdRevTop = rEstsTop[0].low ?? rEstsTop[0].avg;
                else if (_currentScenario === 'bull') dynFwdRevTop = rEstsTop[0].high ?? rEstsTop[0].avg;
                else dynFwdRevTop = rEstsTop[0].avg;
            }
        }

        const simPrice = globalData.current_price;
        const newPeFwd = dynFwdEpsTop > 0 ? simPrice / dynFwdEpsTop : 0;

        const safeProf = globalData.company_profile || {};
        const revenue = globalData.revenue || 0;
        const ebitda = globalData.ebitda || 0;
        const pToB = globalData.price_to_book || 0;
        const dividendRate = globalData.dividend_rate || 0;
        const shares = safeProf.shares_outstanding || 0;
        const bookValuePerShare = (pToB > 0) ? (_realApiPrice / pToB) : 0;

        const newPB = (bookValuePerShare > 0) ? simPrice / bookValuePerShare : 0;
        const newDivYield = (simPrice > 0 && dividendRate > 0) ? (dividendRate / simPrice) * 100 : 0;

        const newMktCap = simPrice * shares;
        const ev = newMktCap + (globalData.total_debt || 0) - (globalData.total_cash || 0);
        const newEvEbitda = (ebitda > 0) ? ev / ebitda : 0;

        let epsGrowth = null;
        if (dynFwdEpsTop && safeProf.trailing_eps && safeProf.trailing_eps > 0) {
            epsGrowth = ((dynFwdEpsTop - safeProf.trailing_eps) / Math.abs(safeProf.trailing_eps)) * 100;
        }
        let revGrowth = null;
        if (dynFwdRevTop && revenue > 0) {
            revGrowth = ((dynFwdRevTop - revenue) / Math.abs(revenue)) * 100;
        }

        const simMetrics = {
            peFwd: newPeFwd,
            evEbitda: newEvEbitda,
            pb: newPB,
            divYield: newDivYield,
            epsGrowth: epsGrowth,
            revGrowth: revGrowth
        };

        if (finalFv != null) {
            window._lastFinalFv = finalFv;
            elements.fairValue.textContent = formatCurrency(finalFv);
            elements.marginSafety.textContent = `${formatPercent(finalMos)} Margin of Safety`;
            elements.marginSafety.style.color = finalMos > 0 ? 'var(--accent)' : 'var(--danger)';
            if (finalMos > 0) {
                elements.marginSafety.style.background = 'rgba(16, 185, 129, 0.2)';
            } else {
                elements.marginSafety.style.background = 'rgba(239, 68, 68, 0.2)';
            }
            if (typeof recalcWithSimPrice === 'function') recalcWithSimPrice(globalData.current_price, true);
        } else {
            elements.fairValue.textContent = 'N/A';
            elements.marginSafety.textContent = 'Valuation not possible';
            elements.marginSafety.style.color = 'var(--text-muted)';
            elements.marginSafety.style.background = 'none';
            if (typeof recalcWithSimPrice === 'function') recalcWithSimPrice(globalData.current_price, true);
        }

        // --- Sync Profile & Metrics Table PEG with Card PEG ---
        const pegTableVal = document.getElementById('metric-val-peg');
        if (pegTableVal && currentPegToDisplay != null && !_simulating) {
            pegTableVal.textContent = currentPegToDisplay.toFixed(2);
        }

        window._currentPegToDisplay = currentPegToDisplay;

        // --- Dynamic UI Re-renders for Scenarios ---
        if (window._renderProfile) window._renderProfile();
        if (window._renderEstimatesTable) window._renderEstimatesTable();

        // If View Data modal is open, simulate a click on the corresponding trigger to refresh it
        const dataModal = document.getElementById('data-modal');
        if (dataModal && dataModal.style.display === 'flex') {
            const activeTitle = document.getElementById('modal-title')?.textContent || '';
            let btnSelector = null;
            if (activeTitle.includes('Discounted Cash Flow')) btnSelector = 'button.view-data-btn[data-method="dcf"]';
            else if (activeTitle.includes('Triangulation')) btnSelector = 'button.view-data-btn[data-method="relative"]';
            else if (activeTitle.includes('Forward Multiple')) btnSelector = 'button.view-data-btn[data-method="peter_lynch"]';
            else if (activeTitle.includes('PEG Valuation')) btnSelector = 'button.view-data-btn[data-method="peg"]';

            if (btnSelector) {
                const btn = document.querySelector(btnSelector);
                if (btn) btn.click();
            }
        }

        const currentScoring = globalData.scoring_results ? globalData.scoring_results[_currentScenario] : null;
        if (currentScoring && currentScoring.rule_of_40) {
            updateRule40UI(currentScoring.rule_of_40);
        }
        
        if (typeof updateScoresDynamic === 'function' && typeof globalData !== 'undefined' && globalData) {
            updateScoresDynamic(globalData.current_price, true);
        }

        // Refresh Comparison Modal if open
        const compModal = document.getElementById('comparison-modal');
        if (compModal && compModal.style.display === 'flex') {
            const prof = globalData.company_profile;
            if (prof && typeof renderComparisonModal === 'function') {
                renderComparisonModal(prof);
            }
        }
    };

    window.triggerRecalculate = updateFairValue;

    const inputSelectors = [
        'fcf-source', 'dcf-years-source', 'dcf-method-selector', 'input-exit-multiple', 'dcf-growth-1-3', 'dcf-growth-4-6', 'dcf-growth-7-8', 'dcf-growth-9-10', 'dcf-custom-wacc', 'dcf-custom-perp',
        'dcf-buyback-source', 'dcf-custom-buyback', 'dcf-custom-sbc', 'relative-variant',
        'lynch-multiple-source', 'lynch-custom-mult', 'lynch-eps-source', 'lynch-custom-growth', 'lynch-return-rate', 'lynch-custom-return',
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

                const limits = {
                    0.75: 30,
                    0.50: 15,
                    0.25: 5
                };
                const pairs = [[g46, 0.75], [g78, 0.50], [g910, 0.25]];
                pairs.forEach(([target, mult]) => {
                    if (!target) return;
                    if (target.value === '' || target.dataset.isDefault === 'true') {
                        target.value = formatCleanInputVal(Math.min(val * mult, limits[mult]));
                        target.dataset.isDefault = 'true';
                        target.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                });
            });
        }

        // Mark as NOT default if the user manually types in any box
        [g13, g46, g78, g910].forEach(target => {
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


    // --- LIVE PRICE POLLING ---
    let livePriceInterval = null;

    const startLivePricePolling = () => {
        if (livePriceInterval) clearInterval(livePriceInterval);

        livePriceInterval = setInterval(async () => {
            if (!currentTicker || _simulating) return; // Don't poll if simulating or no ticker selected

            try {
                const res = await fetch(`/api/live-price/${encodeURIComponent(currentTicker)}`);
                if (!res.ok) return;

                const data = await res.json();
                if (data.price && data.price > 0 && data.price !== globalData.current_price) {
                    console.log(`Live price update for ${currentTicker}: ${data.price}`);

                    // Update global data
                    globalData.current_price = data.price;
                    _realApiPrice = data.price;
                    _originalPrice = data.price;

                    // Update open_price if provided
                    if (data.open_price && globalData.company_profile) {
                        globalData.company_profile.open_price = data.open_price;
                    }

                    // Re-calculate everything with the new price
                    if (typeof recalcWithSimPrice === 'function') {
                        recalcWithSimPrice(data.price, true);
                    }
                }
            } catch (err) {
                console.error("Live price polling error:", err);
            }
        }, 30000); // Poll every 30 seconds
    };

    const analyzeTicker = async (queryParam, forceRefresh = false, silent = false) => {
        const savedScrollY = window.scrollY;
        document.body.classList.add('has-searched');
        if (_simulating && !silent) {
            alert("Cannot search a new ticker while simulating. Resetting to real price first.");
            resetSimulation();
        }

        // v40: Instant UI feedback
        if (!silent) {
            // Clear price trend icons when loading a new ticker
            const ti = document.getElementById('price-trend-icon');
            if (ti) ti.textContent = '';
            const sti = document.getElementById('sticky-price-trend-icon');
            if (sti) sti.textContent = '';
            autocompleteList.style.display = 'none';
            watchlistView.style.display = 'none';
            dashboard.style.display = 'none';
            loadingState.style.display = 'flex';
            if (elements.fairValue) elements.fairValue.textContent = '$0.00';
            if (elements.marginSafety) {
                elements.marginSafety.textContent = '0% Margin of Safety';
                elements.marginSafety.style.background = 'none';
                elements.marginSafety.style.color = 'inherit';
            }
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        if (searchBtn) {
            searchBtn.disabled = true;
            searchBtn.textContent = silent ? 'Updating...' : 'Analyzing...';
        }

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
        if (fcfSourceEl) fcfSourceEl.value = 'revenue';
        const fcfMarginEl = document.getElementById('dcf-custom-fcf-margin');
        if (fcfMarginEl) fcfMarginEl.value = '';
        const fcfMarginGrowthEl = document.getElementById('dcf-custom-margin-growth');
        if (fcfMarginGrowthEl) fcfMarginGrowthEl.value = '0.2';
        const yearsSourceEl = document.getElementById('dcf-years-source');
        if (yearsSourceEl) yearsSourceEl.value = '10yr';

        try {
            // v305: Parallel fetch for valuation AND fresh overrides to prevent cross-device drift
            let valUrl = `/api/valuation/${encodeURIComponent(query)}?t=${Date.now()}`;
            if (forceRefresh) {
                valUrl += `&force_refresh=true`;
            }

            const [valRes, ovRes] = await Promise.all([
                fetch(valUrl),
                fetch(`/api/overrides?t=${Date.now()}`, { cache: 'no-store' })
            ]);

            if (!valRes.ok) throw new Error('Network response was not ok');

            const data = await valRes.json();
            const freshOverrides = await ovRes.json().catch(() => ({}));

            // Sync the global cache before rendering to ensure both mobile and desktop use same rules
            cachedOverrides = freshOverrides || {};

            displayData(data, silent);

            // Auto-load sector peers if none exist
            const prof = globalData.company_profile;
            if (prof && (!prof.competitor_metrics || prof.competitor_metrics.length === 0)) {
                const sectorBtn = document.getElementById('sector-peers-btn');
                if (sectorBtn && !window.isFetchingSectorPeers) {
                    // Slight delay to ensure modal logic is fully settled
                    setTimeout(() => sectorBtn.click(), 50);
                }
            }
        } catch (error) {
            console.error('Error fetching valuation:', error);
            alert('Error: ' + error.message + '\nStack: ' + error.stack);
            loadingState.style.display = 'none';
        } finally {
            if (searchBtn) {
                searchBtn.disabled = false;
                searchBtn.textContent = 'Analyze';
            }
            if (!silent) {
                loadingState.style.display = 'none';
                dashboard.style.display = 'block';
            } else {
                requestAnimationFrame(() => {
                    window.scrollTo(0, savedScrollY);
                });
            }
        }
    };

    const formatCurrency = (val) => val != null ? `$${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'null';
    const formatPercent = (val) => val != null ? `${val.toFixed(2)}%` : '0%';

    const renderOwnership = (ownership) => {
        const ownershipCard = document.getElementById('ownership-card');
        if (!ownership || Object.keys(ownership).length === 0) {
            if (ownershipCard) ownershipCard.style.display = 'none';
            return;
        }
        if (ownershipCard) ownershipCard.style.display = 'block';

        // 1. Holders
        const mh = ownership.major_holders || {};
        const ins = (mh.insiders || 0) * 100;
        const inst = (mh.institutions || 0) * 100;
        const flt = (mh.float || 0) * 100;

        document.getElementById('float-pct-text').textContent = flt.toFixed(1) + '%';
        document.getElementById('leg-insiders').textContent = ins.toFixed(1) + '%';
        document.getElementById('leg-institutions').textContent = inst.toFixed(1) + '%';

        setTimeout(() => {
            document.getElementById('ring-insiders').style.strokeDashoffset = 439.8 - (439.8 * (ins / 100));
            document.getElementById('ring-institutions').style.strokeDashoffset = 339.3 - (339.3 * (inst / 100));
            document.getElementById('ring-float').style.strokeDashoffset = 238.8 - (238.8 * (flt / 100));
        }, 100);

        // 2. Top Holders
        const thBody = document.getElementById('top-holders-body');
        thBody.innerHTML = '';
        if (ownership.top_institutional && ownership.top_institutional.length > 0) {
            ownership.top_institutional.forEach(th => {
                thBody.innerHTML += `<tr>
                    <td>${th.holder}</td>
                    <td style="text-align: right;">${formatBigNumber(th.shares, '')}</td>
                    <td style="text-align: right;">${(th.pct_out * 100).toFixed(2)}%</td>
                    <td style="text-align: right;">${formatBigNumber(th.value, '$')}</td>
                </tr>`;
            });
        } else {
            thBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No data available</td></tr>';
        }

        // 3. Insiders
        const txBody = document.getElementById('insider-tx-body');
        const renderTx = (type) => {
            txBody.innerHTML = '';
            const txs = ownership.insider_transactions ? ownership.insider_transactions[type] : [];
            if (txs && txs.length > 0) {
                txs.forEach(tx => {
                    txBody.innerHTML += `<tr>
                        <td>${tx.date}</td>
                        <td>${tx.insider}<br><span style="color:var(--text-muted); font-size: 0.65rem;">${tx.position}</span></td>
                        <td style="text-align: right; color: ${type === 'buy' ? 'var(--accent)' : 'var(--danger)'};">${formatBigNumber(tx.shares, '')}</td>
                        <td style="text-align: right;">${formatBigNumber(tx.value, '$')}</td>
                    </tr>`;
                });
            } else {
                txBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No transactions found</td></tr>';
            }
        };
        renderTx('buy');

        // Bind sub-tabs for insiders
        document.querySelectorAll('.insider-subtab').forEach(btn => {
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn); // Replace with clone to remove old listeners
            newBtn.addEventListener('click', (e) => {
                document.querySelectorAll('.insider-subtab').forEach(b => {
                    b.classList.remove('active');
                    b.style.background = 'transparent';
                    b.style.color = 'var(--text-muted)';
                    b.style.border = '1px solid rgba(255,255,255,0.2)';
                });

                const type = e.target.getAttribute('data-type');
                e.target.classList.add('active');
                if (type === 'buy') {
                    e.target.style.background = 'rgba(16,185,129,0.2)';
                    e.target.style.color = '#10b981';
                    e.target.style.border = '1px solid #10b981';
                } else {
                    e.target.style.background = 'rgba(239,68,68,0.2)';
                    e.target.style.color = '#ef4444';
                    e.target.style.border = '1px solid #ef4444';
                }
                renderTx(type);
            });
        });

        // 4. Statistics
        const stBody = document.getElementById('insider-stats-body');
        stBody.innerHTML = '';
        if (ownership.insider_purchases_6m && ownership.insider_purchases_6m.length > 0) {
            ownership.insider_purchases_6m.forEach(st => {
                stBody.innerHTML += `<tr>
                    <td>${st.label}</td>
                    <td style="text-align: right;">${formatBigNumber(st.shares, '')}</td>
                    <td style="text-align: right;">${st.trans}</td>
                </tr>`;
            });
        } else {
            stBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">No data available</td></tr>';
        }
    };

    const displayData = (data, isSilentUpdate = false) => {
        startLivePricePolling();
        if (!data) return;

        // Preserve current simulator state locally before overriding globals
        const wasSimulating = _simulating;
        const currentSimInput = document.getElementById('simulate-price-input');
        const currentSimPrice = currentSimInput && !isNaN(parseFloat(currentSimInput.value)) ? parseFloat(currentSimInput.value) : null;

        globalData = data;
        window.globalData = data;
        currentFormulaData = data.formula_data;
        currentTicker = data.ticker;
        const prof = data.company_profile || {};

        if (data.historical_anchors && data.historical_anchors.length > 0) {
            const lastAnchor = data.historical_anchors[0];
            prof.gaap_eps_fy = lastAnchor.eps;
            if (data.historical_data && data.historical_data.years && data.historical_data.eps) {
                const idx = data.historical_data.years.indexOf(lastAnchor.year);
                if (idx !== -1 && idx < data.historical_data.eps.length) {
                    prof.nongaap_eps_fy = data.historical_data.eps[idx];
                }
            }
        }

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

                // Recalculate PEG Sector live based on custom peers
                if (data.formula_data && data.formula_data.peg) {
                    const validPegs = peersList.map(p => {
                        const fwd = parseFloat(p.forward_peg);
                        if (!isNaN(fwd) && fwd > 0) return fwd;
                        return null;
                    }).filter(v => !isNaN(v) && v > 0);
                    if (validPegs.length > 0) {
                        validPegs.sort((a, b) => a - b);
                        const mid = Math.floor(validPegs.length / 2);
                        data.formula_data.peg.industry_peg = (validPegs.length % 2 === 0)
                            ? (validPegs[mid - 1] + validPegs[mid]) / 2
                            : validPegs[mid];
                    }
                }
            } catch (e) {
                console.error("Error loading custom peers", e);
            }
        }

        // Ticker-Specific Weights Logic (v319: Backend archetype weights take priority)
        const override = cachedOverrides[data.ticker] || {};
        const backendArchWeights = data.archetype_weights || null;

        // v319: Detect stale override for Payment Networks where backend identifies a stable moat but DB has 0 DCF
        const storedDcf = override.weights ? (override.weights.dcf ?? 0) : null;
        const isStaleFintechOverride = override.weights && storedDcf === 0 && backendArchWeights && backendArchWeights.dcf > 0;

        if (override.weights && !override._v319_stale && !isStaleFintechOverride) {
            // Restore saved weights for this specific company
            customWeights = { ...override.weights };
        } else if (backendArchWeights) {
            // v319: Use backend archetype-determined weights (replaces old sector-based logic)
            customWeights = setSmartWeights(data.company_profile.sector, data.company_profile.industry, backendArchWeights);
            saveOverride(data.ticker);
            console.log(`v319: Applied archetype weights for ${data.ticker}: ${data.archetype} -> DCF:${customWeights.dcf} Lynch:${customWeights.lynch} PEG:${customWeights.peg} Rel:${customWeights.relative}`);
        } else if (data.company_profile && data.company_profile.sector) {
            // Fallback: No backend weights -> Auto-Set by Sector
            customWeights = setSmartWeights(data.company_profile.sector, data.company_profile.industry);
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

        const stickyName = document.getElementById('sticky-banner-name');
        if (stickyName) stickyName.textContent = data.ticker;

        elements.name.textContent = data.name;
        elements.ticker.textContent = data.ticker;
        elements.currentPrice.textContent = formatCurrency(data.current_price);
        if (data.company_profile && data.company_profile.open_price) {
            animatePriceUI(data.company_profile.open_price, data.current_price, false);
        }

        renderOwnership(data.ownership);

        // Reset Simulate Price mode ONLY if it's a completely new ticker search
        if (!isSilentUpdate) {
            _simulating = false;
            _chartViewActive = false;

            const toggleBtn = document.getElementById('toggle-chart-btn');
            const viewA = document.getElementById('view-fair-value');
            const viewB = document.getElementById('view-price-chart');
            if (toggleBtn && viewA && viewB) {
                toggleBtn.style.background = 'rgba(255,255,255,0.05)';
                toggleBtn.style.borderColor = 'rgba(255,255,255,0.1)';
                viewA.style.display = 'flex';
                viewA.style.opacity = '1';
                viewB.style.display = 'none';
                viewB.style.opacity = '0';
                const openWeightsBtn = document.getElementById('open-weights-btn');
                if (openWeightsBtn) openWeightsBtn.style.display = 'block';
                const fvBox = viewA.closest('.fair-value-box');
                if (fvBox) fvBox.style.minHeight = '';
            }

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
            initChartToggle();
        } else {
            // Update the underlying real prices, but DO NOT disable simulation!
            if (!wasSimulating) {
                _realApiPrice = data.current_price;
                _originalPrice = data.current_price;
            }

            // If we WERE simulating, re-apply the simulated price over the fresh data!
            if (wasSimulating && currentSimPrice !== null) {
                _simulating = true;
                data.current_price = currentSimPrice;
            }
        }

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
                rfBanner.innerHTML = data.red_flags.map(f => `<div style="color: var(--danger); font-weight: bold; font-size: 0.7em; margin-bottom: 0px; display: flex; align-items: center; justify-content: center; text-align: center; white-space: nowrap; letter-spacing: -0.5px; overflow: hidden; text-overflow: ellipsis;">${f}</div>`).join('');
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
            sessionStorage.setItem(`val_v4_${data.ticker.toUpperCase()}`, JSON.stringify({ data, ts: Date.now() }));
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
                        const content = parts[i + 1] ? parts[i + 1].trim() : "";
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
                const deRatio = prof.debt_to_equity;

                if (pe != null && pe > 0) {
                    if (pe > 45) {
                        kpiHtml += `<span style="background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;">🔴 Premium PE (${pe.toFixed(1)}x)</span>`;
                    } else if (pe < 18) {
                        kpiHtml += `<span style="background: rgba(34, 197, 94, 0.12); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;">🟢 Attractive PE (${pe.toFixed(1)}x)</span>`;
                    } else {
                        kpiHtml += `<span style="background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;">🟡 Moderate PE (${pe.toFixed(1)}x)</span>`;
                    }
                }
                if (netMargin != null) {
                    if (netMargin > 1.0) {
                        kpiHtml += `<span style="background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;" title="One-off exceptional gain exceeding 100% of revenue.">⚠️ Exceptional Profit (${(netMargin * 100).toFixed(0)}%)</span>`;
                    } else if (netMargin > 0.20) {
                        kpiHtml += `<span style="background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;">💎 High Margins (${(netMargin * 100).toFixed(0)}%)</span>`;
                    } else if (netMargin < 0.05) {
                        kpiHtml += `<span style="background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;">⚠️ Low Margins (${(netMargin * 100).toFixed(0)}%)</span>`;
                    } else {
                        kpiHtml += `<span style="background: rgba(255, 255, 255, 0.05); color: rgba(255,255,255,0.7); border: 1px solid rgba(255, 255, 255, 0.1); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;">📊 Healthy Margins (${(netMargin * 100).toFixed(0)}%)</span>`;
                    }
                }
                if (deRatio != null) {
                    if (deRatio < 40) {
                        kpiHtml += `<span style="background: rgba(168, 85, 247, 0.12); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;">🛡️ Safe Debt Level</span>`;
                    } else if (deRatio > 150) {
                        kpiHtml += `<span style="background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;">⚠️ High Debt Level (${deRatio.toFixed(0)}%)</span>`;
                    } else {
                        kpiHtml += `<span style="background: rgba(255, 255, 255, 0.05); color: rgba(255,255,255,0.7); border: 1px solid rgba(255, 255, 255, 0.1); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;">⚖️ Balanced Debt</span>`;
                    }
                }

                // AI Semantic Insights Extraction (only if not loading/generating)
                if (!isLoadingAI) {
                    const synthText = (synthesisText || "").toLowerCase();
                    const hasPharma = /phase\s+[i|1|ii|2|iii|3]|clinical|fda|pdufa|pipeline|drug|vaccine|pharma|biotech|clinic|farmaceutic/i.test(synthText);
                    const hasMa = /acquire|acquisition|merger|takeover|bought|transaction|integration|achizi|fuzi/i.test(synthText);
                    const hasSegment = /segment|division|revenue share|growth driver|business unit|segmentation|diviz/i.test(synthText);

                    if (hasPharma) {
                        kpiHtml += `<span class="insight-badge" style="background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box; animation: brief-pulse 2s infinite;" title="Clinical pipeline, FDA decision, or testing phase detected.">🧪 Clinical Catalyst</span>`;
                    }
                    if (hasMa) {
                        kpiHtml += `<span class="insight-badge" style="background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;" title="M&A activity, mergers, or integration costs detected.">🤝 M&A Transaction</span>`;
                    }
                    if (hasSegment) {
                        kpiHtml += `<span class="insight-badge" style="background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.2); font-size: 0.65rem; padding: 3px 8px; border-radius: 12px; font-weight: 700; letter-spacing: 0.3px; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 100%; box-sizing: border-box;" title="Specific analysis on business segments or divisions.">📈 Segment Focus</span>`;
                    }
                }

                let badgeHtml = '';
                if (isLoadingAI) {
                    badgeHtml = `<div id="ai-synthesis-badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); font-size: 0.6rem; padding: 3px 8px; border-radius: 20px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; animation: skeleton-pulse 1.5s infinite;">⏳ GENERATING AI ANALYSIS...</div>`;
                } else if (synthesisText) {
                    badgeHtml = `<div id="ai-synthesis-badge" style="background: linear-gradient(135deg, #38bdf8, #818cf8); color: white; font-size: 0.6rem; padding: 3px 8px; border-radius: 20px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">✨ AI ANALYSIS</div>`;
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
                            <h3 style="font-size: 0.75rem; color: rgba(255,255,255,0.4); margin: 0; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 800; font-family: 'Outfit', sans-serif;">Corporate Summary</h3>
                            ${badgeHtml}
                        </div>
                    </div>
                    
                    <!-- KPI Row -->
                    <div id="brief-kpis" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; max-width: 350px; margin: 0 auto 20px auto; width: 100%;">
                        ${kpiHtml}
                    </div>

                    <!-- Tabs Navigation -->
                    <div style="display: flex; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px; gap: 10px; overflow-x: auto; scrollbar-width: none;">
                        <button class="brief-tab ${activeTab === 'overview' ? 'active' : ''}" data-tab="overview">🏢 Overview</button>
                        <button class="brief-tab ${activeTab === 'swot' ? 'active' : ''}" data-tab="swot">⚖️ SWOT Analysis</button>
                        <button class="brief-tab ${activeTab === 'news' ? 'active' : ''}" data-tab="news">📰 Market News</button>
                    </div>

                    <!-- Active Tab Content -->
                    <div id="brief-panel-content" style="font-size: 0.9rem; line-height: 1.6; color: rgba(255,255,255,0.85); max-height: 250px; overflow-y: auto; padding-right: 6px; font-family: 'Outfit', sans-serif;"></div>
                    
                    <div style="display: flex; justify-content: flex-end; margin-top: 10px;">
                        <button id="copy-brief-btn" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 4px 8px; color: rgba(255,255,255,0.7); cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 0.72rem; transition: all 0.2s; font-family: 'Outfit', sans-serif;" title="Copy summary to clipboard">
                            <span style="font-size: 0.8rem;">📋</span> <span id="copy-brief-text">Copy</span>
                        </button>
                    </div>
                `;

                const renderActivePanel = () => {
                    const panel = document.getElementById('brief-panel-content');
                    if (!panel) return;

                    if (activeTab === 'overview') {
                        if (isLoadingAI) {
                            panel.innerHTML = `
                                <div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 8px; color: white;">
                                    ${prof.name || 'The company'} is classified in the <span style="color:#38bdf8;">${prof.sector || 'N/A'}</span> sector, <span style="color:#38bdf8;">${prof.industry || 'N/A'}</span> industry.
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
                                    ${prof.name || 'The company'} is classified in the <span style="color:#38bdf8;">${prof.sector || 'N/A'}</span> sector, <span style="color:#38bdf8;">${prof.industry || 'N/A'}</span> industry.
                                </div>
                                <p style="margin: 0; color: rgba(255,255,255,0.8); line-height: 1.6; text-align: justify;">
                                    ${parsed.executiveSummary || prof.business_summary || 'No concise description available.'}
                                </p>
                            `;
                        }
                    } else if (activeTab === 'swot') {
                        if (isLoadingAI) {
                            panel.innerHTML = `
                                <div style="display: flex; flex-direction: row; flex-wrap: wrap; gap: 15px; width: 100%;">
                                    <div style="flex: 1 1 280px; min-width: 250px;">
                                        <h4 style="color: #4ade80; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Strategic Strengths</h4>
                                        <div class="skeleton-text" style="width: 100%; height: 35px; border-radius: 6px;"></div>
                                        <div class="skeleton-text" style="width: 100%; height: 35px; border-radius: 6px;"></div>
                                    </div>
                                    <div style="flex: 1 1 280px; min-width: 250px;">
                                        <h4 style="color: #f87171; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Vulnerabilities & Risks</h4>
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
                                : '<div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; padding: 10px; font-style:italic;">Diversified commercial operations.</div>';

                            const risksHtml = parsed.vulnerabilitiesRisks.length > 0
                                ? parsed.vulnerabilitiesRisks.map(r => `
                                    <div style="display: flex; gap: 10px; margin-bottom: 8px; align-items: flex-start; background: rgba(239, 68, 68, 0.04); border: 1px solid rgba(239, 68, 68, 0.1); padding: 8px 12px; border-radius: 6px;">
                                        <span style="color: #f87171; font-weight: bold; font-size: 0.9rem; flex-shrink:0;">⚠️</span>
                                        <span style="color: rgba(255,255,255,0.85); font-size: 0.8rem;">${r}</span>
                                    </div>`).join('')
                                : '<div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; padding: 10px; font-style:italic;">Exposure to global market cycles.</div>';

                            panel.innerHTML = `
                                <div style="display: flex; flex-direction: row; flex-wrap: wrap; gap: 15px; width: 100%;">
                                    <div style="flex: 1 1 280px; min-width: 250px;">
                                        <h4 style="color: #4ade80; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Strategic Strengths</h4>
                                        ${strengthsHtml}
                                    </div>
                                    <div style="flex: 1 1 280px; min-width: 250px;">
                                        <h4 style="color: #f87171; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Vulnerabilities & Risks</h4>
                                        ${risksHtml}
                                    </div>
                                </div>
                            `;
                        }
                    } else if (activeTab === 'news') {
                        if (isLoadingAI && !globalData.latest_news) {
                            panel.innerHTML = `
                                <div class="brief-news-item"><div class="skeleton-text" style="width: 80%;"></div><div class="skeleton-text" style="width: 50%;"></div></div>
                                <div class="brief-news-item"><div class="skeleton-text" style="width: 75%;"></div><div class="skeleton-text" style="width: 45%;"></div></div>
                            `;
                        } else if (globalData.latest_news && globalData.latest_news.length > 0) {
                            panel.innerHTML = globalData.latest_news.map((news, index) => {
                                const title = news.title;
                                const source = news.publisher;

                                return `
                                    <div class="brief-news-item" style="cursor: pointer;" onclick="window.openNewsModalByIndex(${index})">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; gap: 10px;">
                                            <span style="background: rgba(56, 189, 248, 0.1); color: #38bdf8; font-size: 0.58rem; padding: 2px 6px; border-radius: 4px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.3px;">${source}</span>
                                        </div>
                                        <div style="color: rgba(255,255,255,0.9); font-size: 0.8rem; line-height: 1.4; font-weight: 600;">${title}</div>
                                    </div>
                                `;
                            }).join('');
                        } else if (parsed.latestMarketIntelligence.length > 0) {
                            panel.innerHTML = parsed.latestMarketIntelligence.map((item, index) => {
                                const match = item.match(/^(.*?)\s*\(Source:\s*(.*?)\)$/i);
                                const title = match ? match[1] : item;
                                const source = match ? match[2] : "Market News";

                                // Synthesize a fake news object so the modal can still open using the text data
                                const synthesizedNews = {
                                    title: title,
                                    publisher: source,
                                    summary: "Acesta este un fragment generat din inteligența pieței. Pentru articolul complet sau sumarul detaliat, vă rugăm să actualizați datele."
                                };

                                // Inject into globalData so openNewsModalByIndex works
                                if (!globalData.latest_news) globalData.latest_news = [];
                                globalData.latest_news[index] = synthesizedNews;

                                return `
                                    <div class="brief-news-item" style="cursor: pointer;" onclick="window.openNewsModalByIndex(${index})">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; gap: 10px;">
                                            <span style="background: rgba(56, 189, 248, 0.1); color: #38bdf8; font-size: 0.58rem; padding: 2px 6px; border-radius: 4px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.3px;">${source}</span>
                                        </div>
                                        <div style="color: rgba(255,255,255,0.9); font-size: 0.8rem; line-height: 1.4; font-weight: 600;">${title}</div>
                                    </div>
                                `;
                            }).join('');
                        } else {
                            panel.innerHTML = '<div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; padding: 20px; text-align: center; font-style:italic;">No recent news or market developments available.</div>';
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
                            copyText.textContent = 'Copied!';
                            copyBtn.style.background = 'rgba(34, 197, 94, 0.15)';
                            copyBtn.style.color = '#4ade80';
                            copyBtn.style.borderColor = 'rgba(34, 197, 94, 0.3)';
                            setTimeout(() => {
                                copyText.textContent = 'Copy';
                                copyBtn.style.background = 'rgba(255,255,255,0.05)';
                                copyBtn.style.color = 'rgba(255,255,255,0.7)';
                                copyBtn.style.borderColor = 'rgba(255,255,255,0.1)';
                            }, 2000);
                        });
                    };
                }
            };

            // Determine if the loaded synthesis is just a fallback (either empty, or containing our specific fallback marker)
            const synthTextLower = (data.company_overview_synthesis || "").toLowerCase();
            const isFallback = !data.company_overview_synthesis ||
                synthTextLower.includes("generation is active") ||
                synthTextLower.includes("generarea analizei ai este activ");

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
        const dcfCardMos = document.getElementById('dcf-card-mos');
        if (dcfCardMosRow && data.formula_data && data.formula_data.dcf) {
            const dcf = data.formula_data.dcf;
            dcfCardMosRow.style.display = 'flex';
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

        // Dynamically load the current scenario's Buy Score
        if (data.scoring_results && data.scoring_results[_currentScenario]) {
            data.good_to_buy_total = data.scoring_results[_currentScenario].good_to_buy_total;
            data.buy_breakdown = data.scoring_results[_currentScenario].buy_breakdown;
        }

        currentBuyBreakdown = data.buy_breakdown;
        _originalBuyBreakdown = JSON.parse(JSON.stringify(data.buy_breakdown));
        _originalBuyScore = data.good_to_buy_total;

        // Check if High Growth mode was activated by backend
        window.isHighGrowthModel = currentBuyBreakdown && currentBuyBreakdown.some(item => item.metric && item.metric.includes("Rule of 40"));

        currentPiotroskiBreakdown = data.piotroski_breakdown || (data.piotroski && data.piotroski.breakdown) || [];

        updateScoreUI(data.health_score_total, 'health-score-circle', 'health-score-fill');
        updateScoreUI(data.good_to_buy_total, 'buy-score-circle', 'buy-score-fill');

        const container = document.querySelector('#buy-score-card span.label');
        if (container) {
            let badge = container.querySelector('.hg-badge');
            if (window.isHighGrowthModel) {
                if (!badge) {
                    badge = document.createElement('span');
                    badge.className = 'hg-badge';
                    badge.style.marginLeft = '10px';
                    badge.style.fontSize = '0.7rem';
                    badge.style.background = 'linear-gradient(90deg, #ec4899, #f43f5e)';
                    badge.style.color = 'white';
                    badge.style.padding = '2px 8px';
                    badge.style.borderRadius = '12px';
                    badge.style.fontWeight = 'bold';
                    badge.style.verticalAlign = 'middle';
                    badge.textContent = '🚀 High-Growth Model';
                    container.appendChild(badge);
                }
            } else if (badge) {
                badge.remove();
            }
        }
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


        // Beneish M-Score UI Update
        const beneishData = data.health_score ? data.health_score.beneish : null;
        updateBeneishUI(beneishData);

        const bRow = document.getElementById('beneish-score-row');
        if (bRow) {
            bRow.style.cursor = 'pointer';
            bRow.onclick = () => {
                renderBeneishBreakdown(beneishData);
            };
        }

        // Rule of 40 UI Update & Click Binding
        updateRule40UI(data.rule_of_40);
        const rule40Row = document.getElementById('rule40-score-row');
        if (rule40Row) {
            rule40Row.style.cursor = 'pointer';
            rule40Row.onclick = () => {
                const currentScoring = globalData.scoring_results ? globalData.scoring_results[_currentScenario || 'base'] : null;
                const r40Data = (currentScoring && currentScoring.rule_of_40) ? currentScoring.rule_of_40 : globalData.rule_of_40;
                renderRule40Breakdown(r40Data);
            };
        }

        // UPDATED: Sync both MOS and PEG to the Score Breakdown dynamically

        // v290: Scenario-aware DCF Growth Logic
        window.getDcfGrowthDefault = (data) => {
            if (!data) return 10.0;
            let val = 8.0;
            if (data.computed_dcf_growth != null) {
                val = Math.round(data.computed_dcf_growth * 1000) / 10;
            } else if (data.company_profile && data.company_profile.revenue_growth != null) {
                val = Math.round(data.company_profile.revenue_growth * 1000) / 10;
            }
            return Math.min(val, 50.0);
        };

        // Skip DCF input reinitialization on silent updates (peer changes)
        // to preserve user-modified DCF parameters
        if (!isSilentUpdate) {
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
        }
        updateFairValue();

        // Ensure UI displays current global state immediately after updateFairValue recalculates it.
        // Final updates to MOS styling based on fallback or custom weights.
        if (elements.fairValue && elements.marginSafety && globalData.fair_value != null && globalData.margin_of_safety != null) {
            elements.fairValue.textContent = formatCurrency(globalData.fair_value);
            elements.marginSafety.textContent = `${formatPercent(globalData.margin_of_safety)} Margin of Safety`;
            elements.marginSafety.style.color = globalData.margin_of_safety > 0 ? 'var(--accent)' : 'var(--danger)';
            elements.marginSafety.style.background = globalData.margin_of_safety > 0 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)';
        }

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
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 290px), 1fr)); gap: 2.5rem;">
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
                                        <button id="compare-peers-btn" class="peer-btn" style="margin:0;">📊 PEERS</button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Column 2: Valuation -->
                        <div class="profile-section">
                            <div style="font-size: 0.8rem; color: var(--text-main); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid rgba(255,255,255,0.1); font-weight: 700;">Valuation & Earnings</div>
                            <div style="display: flex; flex-direction: column;">
                                ${(() => {
                        let dynFwdEps = prof.fwd_eps;
                        let dynFwdRev = prof.forward_revenue;

                        if (globalData.eps_estimates) {
                            const eEsts = globalData.eps_estimates.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
                            if (eEsts.length >= 1) {
                                if (_currentScenario === 'bear') dynFwdEps = eEsts[0].low ?? eEsts[0].avg;
                                else if (_currentScenario === 'bull') dynFwdEps = eEsts[0].high ?? eEsts[0].avg;
                                else dynFwdEps = eEsts[0].avg;
                            }
                        }
                        if (globalData.rev_estimates) {
                            const rEsts = globalData.rev_estimates.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
                            if (rEsts.length >= 1) {
                                if (_currentScenario === 'bear') dynFwdRev = rEsts[0].low ?? rEsts[0].avg;
                                else if (_currentScenario === 'bull') dynFwdRev = rEsts[0].high ?? rEsts[0].avg;
                                else dynFwdRev = rEsts[0].avg;
                            }
                        }

                        let simActive = (typeof window._simulatedPriceActive !== 'undefined' && window._simulatedPriceActive !== null);
                        let p = simActive ? window._simulatedPriceActive : (_originalPrice || _realApiPrice);
                        let mCap = simActive ? (p * prof.shares_outstanding) : prof.market_cap;
                        let simStyle = simActive ? 'color: #fbbf24;' : '';

                        let dynFwdPe = dynFwdEps && dynFwdEps > 0 && p ? p / dynFwdEps : prof.fwd_pe;
                        let dynFwdPs = dynFwdRev && dynFwdRev > 0 && mCap ? (mCap / dynFwdRev) : prof.fwd_ps;
                        // v319: Use backend-calculated PEG (Non-GAAP based) instead of Yahoo's stale peg_ratio
                        let backendPeg = globalData?.formula_data?.peg?.current_peg || prof.peg_ratio || null;
                        let pegRatio = simActive && window._currentPegToDisplay != null ? window._currentPegToDisplay : backendPeg;

                        let peTtm = prof.trailing_eps && prof.trailing_eps > 0 ? (p / prof.trailing_eps) : prof.trailing_pe;
                        let peGaap = prof.gaap_eps_fy && prof.gaap_eps_fy > 0 ? (p / prof.gaap_eps_fy) : null;
                        let peNonGaap = prof.adjusted_eps && prof.adjusted_eps > 0 ? (p / prof.adjusted_eps) : null;

                        let ps = globalData.revenue && globalData.revenue > 0 ? (mCap / globalData.revenue) : prof.ps_ratio;
                        let pfcf = globalData.fcf && globalData.fcf > 0 ? (mCap / globalData.fcf) : prof.pfcf_ratio;

                        return `
                                        ${metricRow('P/E TTM', peTtm ? peTtm.toFixed(2) + 'x' : 'N/A', '', simStyle)}
                                        ${metricRow('P/E GAAP', peGaap ? peGaap.toFixed(2) + 'x' : 'N/A', '', simStyle)}
                                        ${metricRow('P/E Non-GAAP', peNonGaap ? peNonGaap.toFixed(2) + 'x' : 'N/A', '', simStyle)}
                                        ${metricRow('5Y Avg. P/E', prof.historic_pe ? prof.historic_pe.toFixed(2) + 'x' : 'N/A')}
                                        ${metricRow('P/E FWD', dynFwdPe ? dynFwdPe.toFixed(2) + 'x' : 'N/A', '', simStyle)}
                                        ${metricRow('EPS Diluted', prof.gaap_eps_fy ? '$' + prof.gaap_eps_fy.toFixed(2) : (prof.gaap_eps ? '$' + prof.gaap_eps.toFixed(2) : (prof.trailing_eps ? '$' + prof.trailing_eps.toFixed(2) : 'N/A')))}
                                        ${metricRow('EPS Non-GAAP', prof.adjusted_eps ? '$' + prof.adjusted_eps.toFixed(2) : 'N/A')}
                                        ${metricRow('FWD EPS', dynFwdEps ? '$' + dynFwdEps.toFixed(2) : 'N/A')}
                                        ${metricRow('PEG', pegRatio != null ? pegRatio.toFixed(2) : 'N/A', '', simStyle)}
                                        ${metricRow('P/S', ps ? ps.toFixed(2) + 'x' : 'N/A', '', simStyle)}
                                        ${metricRow('P/S FWD', dynFwdPs ? dynFwdPs.toFixed(2) + 'x' : 'N/A', '', simStyle)}
                                        ${metricRow('P/FCF', pfcf ? pfcf.toFixed(2) + 'x' : 'N/A', '', simStyle)}
                                    `;
                    })()}
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

                if (document.getElementById('compare-peers-btn')) {
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
                    { label: 'FCF Margin', key: 'fcf_margin_pct', formatter: v => (v != null) ? v : 'N/A', sparkKey: 'fcf_margin_pct' },
                    { label: 'Net Income (B)', key: 'net_income_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'net_income_b' },
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
                    const pts = cleanValues.map((v, i) => `${(i / (cleanValues.length - 1)) * w},${h - ((v - min) / range) * h}`).join(' ');
                    const color = cleanValues[cleanValues.length - 1] >= cleanValues[0] ? '#10b981' : '#ef4444';
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

        // Show deep research section (hidden by default to prevent empty state on page load)
        const deepResearch = document.getElementById('deep-research-section');
        if (deepResearch) deepResearch.style.display = '';

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
        'dcf-buyback-source', 'dcf-custom-buyback', 'dcf-custom-sbc', 'relative-variant',
        'lynch-multiple-source', 'lynch-custom-mult', 'lynch-eps-source', 'lynch-custom-growth', 'lynch-return-rate', 'lynch-custom-return',
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
            piotroski_score: pScore,
            sector_median_peg: globalData?.formula_data?.peg?.industry_peg || null
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
            weights: customWeights,
            custom_scenarios: window._customScenariosData || null
        };

        cachedOverrides[ticker] = payload;

        fetch('/api/overrides', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(() => {
            sessionStorage.removeItem(`val_v4_${ticker.toUpperCase()}`);
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
            weights: { ...customWeights },
            custom_scenarios: window._customScenariosData || null
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

        // If there are no overrides for this ticker, clear out any custom scenarios
        // so they don't bleed over from a previously viewed ticker.
        if (!ov) {
            window._customScenariosData = null;
            const customScenariosBtn = document.getElementById('open-custom-scenarios-btn');
            if (customScenariosBtn) {
                customScenariosBtn.classList.remove('active-custom');
            }
            document.querySelectorAll('.cs-input').forEach(inp => inp.value = '');
            return false;
        }
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

        // Restore Custom Scenarios Data
        if (ov.custom_scenarios) {
            window._customScenariosData = ov.custom_scenarios;
            const customScenariosBtn = document.getElementById('open-custom-scenarios-btn');
            if (customScenariosBtn) {
                customScenariosBtn.classList.add('active-custom');
            }
        } else {
            window._customScenariosData = null;
            const customScenariosBtn = document.getElementById('open-custom-scenarios-btn');
            if (customScenariosBtn) {
                customScenariosBtn.classList.remove('active-custom');
            }
        }

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
            .then(() => sessionStorage.removeItem(`val_v4_${ticker.toUpperCase()}`))
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
                dcf: ['fcf-source', 'dcf-years-source', 'dcf-method-selector', 'input-exit-multiple', 'dcf-growth-1-3', 'dcf-growth-4-6', 'dcf-growth-7-8', 'dcf-growth-9-10', 'dcf-custom-wacc', 'dcf-custom-perp', 'dcf-custom-fcf-margin', 'dcf-custom-margin-growth', 'dcf-buyback-source', 'dcf-custom-buyback', 'dcf-custom-sbc'],
                relative: ['relative-variant', 'rel-weight-mode-card'],
                peter_lynch: ['lynch-multiple-source', 'lynch-custom-mult', 'lynch-eps-source', 'lynch-custom-growth', 'lynch-return-rate', 'lynch-custom-return'],
                peg: ['peg-eps-source', 'peg-custom-growth', 'peg-mode']
            };

            (idsToReset[method] || []).forEach(id => {
                delete ov.inputs[id];
            });

            saveOverridesToServer(currentTicker, ov);
        }

        // 2. Re-apply baseline overrides (if any left)
        applyOverrides(currentTicker);

        // 3. FORCE re-population of specific fields for THIS method
        if (method === 'dcf') {
            // Reset Dropdowns
            ['fcf-source', 'dcf-buyback-source', 'dcf-method-selector', 'dcf-years-source'].forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.value = (id === 'fcf-source') ? 'revenue' :
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
            if (relVar) relVar.dispatchEvent(new Event('change', { bubbles: true }));
            if (relWeight) relWeight.dispatchEvent(new Event('change', { bubbles: true }));
        } else if (method === 'peter_lynch') {
            const lMult = document.getElementById('lynch-multiple-source');
            if (lMult) lMult.value = 'system';
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
            e.preventDefault();
            const button = e.target.closest('.reset-btn');
            if (!button) return;
            const method = button.getAttribute('data-method');
            if (confirm(`Reset ${method.toUpperCase()} to defaults?`)) {
                if (method === 'peers') {
                    if (globalData.company_profile && globalData.company_profile.original_competitor_metrics) {
                        globalData.company_profile.competitor_metrics = JSON.parse(JSON.stringify(globalData.company_profile.original_competitor_metrics));
                        localStorage.removeItem('customPeers_' + globalData.ticker);
                        displayData(globalData);
                    }
                } else {
                    resetMethodDefaults(method);
                }
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
                        y: {
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

        // V304: Prevent previous company's closure from persisting if new company fails to load estimates
        window._renderEstimatesTable = null;

        analystCard.style.setProperty('display', 'block', 'important');
        document.getElementById('pt-avg').textContent = '...';
        document.getElementById('rec-status').textContent = '...';
        const eBody = document.querySelector('#eps-est-table tbody');
        const rBody = document.querySelector('#rev-est-table tbody');
        if (eBody) eBody.innerHTML = '';
        if (rBody) rBody.innerHTML = '';

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

            // Tables population exported for re-rendering on scenario switch
            const eItems = data.eps_estimates || [];
            const rItems = data.rev_estimates || [];
            window._renderEstimatesTable = () => {
                const eBody = document.querySelector('#eps-est-table tbody');
                const rBody = document.querySelector('#rev-est-table tbody');
                if (eBody) eBody.innerHTML = '';
                if (rBody) rBody.innerHTML = '';

                const epsHead = document.querySelector('#eps-est-table thead tr');
                const revHead = document.querySelector('#rev-est-table thead tr');
                const headerLabel = _currentScenario === 'bear' ? 'Low' : (_currentScenario === 'bull' ? 'High' : 'Avg');
                if (epsHead) epsHead.innerHTML = `<th>Period</th><th style="text-align:right">${headerLabel}</th><th style="text-align:right">Growth</th>`;
                if (revHead) revHead.innerHTML = `<th>Period</th><th style="text-align:right">${headerLabel}</th><th style="text-align:right">Growth</th>`;


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

                let prevEpsVal = null;
                let epsGrowths = [];

                eItems.forEach((item, idx) => {
                    if (!item) return;
                    const pLabel = item.period || '--';
                    const isAnchor = item.status === 'reported';

                    let scenarioVal = item.avg;
                    if (!isAnchor) {
                        if (_currentScenario === 'bear' && item.low != null) scenarioVal = item.low ?? item.avg;
                        if (_currentScenario === 'bull' && item.high != null) scenarioVal = item.high ?? item.avg;
                    }

                    const aVal = (scenarioVal != null) ? formatLargeNumber(parseFloat(scenarioVal), '$') : '--';
                    let gVal = isAnchor ? '' : '--';

                    if (!isAnchor) {
                        let dynamicBase = prevEpsVal;

                        if (item.status === 'reported' && item.surprise_pct != null) {
                            gVal = (parseFloat(item.surprise_pct) * 100).toFixed(1) + '%';
                        } else if (scenarioVal != null && dynamicBase != null && dynamicBase !== 0) {
                            let gRaw = (parseFloat(scenarioVal) - parseFloat(dynamicBase)) / Math.abs(parseFloat(dynamicBase));
                            epsGrowths.push(gRaw);
                            gVal = (gRaw * 100).toFixed(1) + '%';
                        } else if (item.growth != null) {
                            let gRaw = parseFloat(item.growth);
                            epsGrowths.push(gRaw);
                            gVal = (gRaw * 100).toFixed(1) + '%';
                        }
                    }

                    prevEpsVal = scenarioVal; // carry forward sequentially

                    const sColor = isAnchor ? 'white' : getColor(item);
                    const weight = item.status === 'reported' ? 'bold' : 'normal';
                    const labelColor = isAnchor ? 'white' : (item.status === 'reported' ? '#4ade80' : 'inherit');
                    const valColor = isAnchor ? 'white' : 'inherit';
                    const estVal = item.num_estimates != null ? item.num_estimates : '--';

                    if (eBody) eBody.innerHTML += `<tr><td style="padding:4px 0;color:${labelColor};">${pLabel}</td><td style="text-align:right;color:${valColor};">${aVal}</td><td style="text-align:right;color:${sColor};font-weight:${weight};">${gVal}</td></tr>`;
                });

                if (globalData) {
                    if (epsGrowths.length >= 2) globalData.computed_eps_growth = (epsGrowths[0] + epsGrowths[1]) / 2.0;
                    else if (epsGrowths.length === 1) globalData.computed_eps_growth = epsGrowths[0];
                }

                let prevRevVal = null;
                let revGrowths = [];

                rItems.forEach((item, idx) => {
                    if (!item) return;
                    const pLabel = item.period || '--';
                    const isAnchor = item.status === 'reported';

                    let scenarioVal = item.avg;
                    if (!isAnchor) {
                        if (_currentScenario === 'bear' && item.low != null) scenarioVal = item.low ?? item.avg;
                        if (_currentScenario === 'bull' && item.high != null) scenarioVal = item.high ?? item.avg;
                    }

                    const aVal = (scenarioVal != null) ? formatLargeNumber(parseFloat(scenarioVal), '$') : '--';
                    let gVal = isAnchor ? '' : '--';

                    if (!isAnchor) {
                        let dynamicBase = prevRevVal;
                        if (scenarioVal != null && dynamicBase != null && dynamicBase !== 0) {
                            let gRaw = (parseFloat(scenarioVal) / parseFloat(dynamicBase)) - 1;
                            revGrowths.push(gRaw);
                            gVal = (gRaw * 100).toFixed(1) + '%';
                        } else if (item.growth != null) {
                            let gRaw = parseFloat(item.growth);
                            revGrowths.push(gRaw);
                            gVal = (gRaw * 100).toFixed(1) + '%';
                        }
                    }

                    prevRevVal = scenarioVal; // carry forward sequentially

                    const sColor = isAnchor ? 'white' : getColor(item);
                    const weight = item.status === 'reported' ? 'bold' : 'normal';
                    const labelColor = isAnchor ? 'white' : (item.status === 'reported' ? '#4ade80' : 'inherit');
                    const valColor = isAnchor ? 'white' : 'inherit';

                    if (rBody) rBody.innerHTML += `<tr><td style="padding:4px 0;color:${labelColor};">${pLabel}</td><td style="text-align:right;color:${valColor};">${aVal}</td><td style="text-align:right;color:${sColor};font-weight:${weight};">${gVal}</td></tr>`;
                });

                if (globalData) {
                    if (revGrowths.length >= 2) globalData.computed_dcf_growth = (revGrowths[0] + revGrowths[1]) / 2.0;
                    else if (revGrowths.length === 1) globalData.computed_dcf_growth = revGrowths[0];
                }

            }; // End window._renderEstimatesTable
            window._renderEstimatesTable(); // Call it immediately

            // -------------------------------------------------------------
            // Sync analyst estimates data to globalData FIRST
            // -------------------------------------------------------------
            if (globalData && ticker) {
                globalData.rev_estimates = rItems;
                globalData.eps_estimates = eItems;

                const g13 = document.getElementById('dcf-growth-1-3');
                if (g13) {
                    const hadOverrides = (cachedOverrides[globalData.ticker] && cachedOverrides[globalData.ticker].inputs && cachedOverrides[globalData.ticker].inputs['dcf-growth-1-3']);
                    if (!hadOverrides) {
                        const targetGrowth = window.getDcfGrowthDefault(globalData);
                        g13.value = formatCleanInputVal(targetGrowth);
                        // Cascade to other inputs using 'change' as 'input' is not caught on text inputs
                        g13.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }

                // Re-calculate all fair values to reflect the fresh consensus growth
                if (typeof updateFairValue === 'function') updateFairValue();
            }

            // -------------------------------------------------------------
            // v70: Reactive Chart Updates - Link Analyst Projections to the main Stability Chart
            // -------------------------------------------------------------
            try {
                if ((chartEpsShares || chartRevFcf) && (eItems.length > 0 || rItems.length > 0)) {
                    console.log("[Analyst] Synchronizing projections to historical charts...");

                    // 1. Sync EPS (Chart 2)
                    if (chartEpsShares && eItems.length > 0 && chartEpsShares.data) {
                        const labels = chartEpsShares.data.labels || [];
                        const epsDs = (chartEpsShares.data.datasets || []).find(d => d.label === 'EPS ($)');
                        const sharesDs = (chartEpsShares.data.datasets || []).find(d => d.label === 'Shares (B)');
                        if (epsDs && epsDs.data) {
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
                                            if (sharesDs && sharesDs.data && (sharesDs.data[idx] === 0 || sharesDs.data[idx] == null)) {
                                                let lastActualIdx = -1;
                                                for (let i = labels.length - 1; i >= 0; i--) {
                                                    if (!String(labels[i]).includes('Est')) {
                                                        lastActualIdx = i;
                                                        break;
                                                    }
                                                }
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
                    if (chartRevFcf && rItems.length > 0 && chartRevFcf.data) {
                        const labels = chartRevFcf.data.labels || [];
                        const revDs = (chartRevFcf.data.datasets || []).find(d => d.label === 'Revenue ($B)');
                        const fcfDs = (chartRevFcf.data.datasets || []).find(d => d.label === 'FCF ($B)');
                        if (revDs && revDs.data) {
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
                                            if (fcfDs && fcfDs.data && (fcfDs.data[idx] === 0 || fcfDs.data[idx] == null)) {
                                                let lastActualIdx = -1;
                                                for (let i = labels.length - 1; i >= 0; i--) {
                                                    if (!String(labels[i]).includes('Est')) {
                                                        lastActualIdx = i;
                                                        break;
                                                    }
                                                }
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
            } catch (chartErr) {
                console.warn("[Analyst] Failed to sync to charts:", chartErr);
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

    // Scenario Toggles

    // --- CUSTOM SCENARIOS LOGIC ---
    const customScenariosBtn = document.getElementById('open-custom-scenarios-btn');
    const customScenariosModal = document.getElementById('custom-scenarios-modal');
    const closeCustomScenariosBtn = document.getElementById('close-custom-scenarios-modal');
    const calculateCustomBtn = document.getElementById('cs-calculate-btn');
    const resetCustomBtn = document.getElementById('cs-reset-btn');
    const turnOffCustomBtn = document.getElementById('cs-turn-off-btn');

    if (customScenariosBtn) {
        customScenariosBtn.addEventListener('click', () => {
            if (customScenariosModal) {
                // Populate inputs if data exists
                if (window._customScenariosData) {
                    ['bear', 'base', 'bull'].forEach(scen => {
                        const data = window._customScenariosData[scen];
                        if (!data) return;
                        if (data.rev13 !== null) document.getElementById(`cs-rev-1-3-${scen}`).value = data.rev13;
                        if (data.fcfMargin !== null) document.getElementById(`cs-fcf-margin-${scen}`).value = data.fcfMargin;
                        if (data.wacc !== null) document.getElementById(`cs-wacc-${scen}`).value = data.wacc;
                        if (data.exit !== null) document.getElementById(`cs-exit-${scen}`).value = data.exit;
                        if (data.perp !== null) document.getElementById(`cs-perp-${scen}`).value = data.perp;
                        if (data.eps !== null) document.getElementById(`cs-eps-${scen}`).value = data.eps;
                        if (data.pe !== null) document.getElementById(`cs-pe-${scen}`).value = data.pe;
                    });
                }
                customScenariosModal.style.display = 'flex';
            }
        });
    }

    if (closeCustomScenariosBtn) {
        closeCustomScenariosBtn.addEventListener('click', () => {
            if (customScenariosModal) customScenariosModal.style.display = 'none';
        });
    }
    if (customScenariosModal) {
        customScenariosModal.addEventListener('click', (e) => {
            if (e.target === customScenariosModal) {
                customScenariosModal.style.display = 'none';
            }
        });
    }

    // Growth Tips Tooltip Logic
    const tipsTooltip = document.getElementById('cs-tips-tooltip');
    const tipsContent = document.getElementById('cs-tips-content');
    const revInputs = document.querySelectorAll('#cs-rev-1-3-bear, #cs-rev-1-3-base, #cs-rev-1-3-bull');

    revInputs.forEach(input => {
        input.addEventListener('focus', (e) => {
            if (!globalData || !globalData.company_profile) return;
            const prof = globalData.company_profile;

            // Calculate historically available data
            let rev1y = 'N/A';
            let rev3y = 'N/A';
            if (globalData.financials && globalData.financials.length >= 2) {
                const f = globalData.financials;
                const r0 = f[0].total_revenue;
                const r1 = f[1].total_revenue;
                if (r0 > 0 && r1 > 0) rev1y = ((r0 / r1) - 1) * 100;

                if (f.length >= 4) {
                    const r3 = f[3].total_revenue;
                    if (r0 > 0 && r3 > 0) rev3y = (Math.pow(r0 / r3, 1/3) - 1) * 100;
                }
            }

            let fwdAvg = 'N/A';
            if (globalData.computed_dcf_growth != null) {
                 fwdAvg = globalData.computed_dcf_growth * 100;
            } else if (prof.revenue_growth != null) {
                 fwdAvg = prof.revenue_growth * 100;
            }

            const formatVal = (v) => v !== 'N/A' && !isNaN(v) ? v.toFixed(1) + '%' : 'N/A';

            tipsContent.innerHTML = `
                <div style="display:flex; justify-content:space-between; width:120px; margin-bottom:3px;"><span style="color:var(--text-muted);">1Y Hist:</span> <span>${formatVal(rev1y)}</span></div>
                <div style="display:flex; justify-content:space-between; width:120px; margin-bottom:3px;"><span style="color:var(--text-muted);">3Y CAGR:</span> <span>${formatVal(rev3y)}</span></div>
                <div style="display:flex; justify-content:space-between; width:120px;"><span style="color:var(--text-muted);">FWD Est:</span> <span style="color:#fbbf24;">${formatVal(fwdAvg)}</span></div>
            `;

            tipsTooltip.style.display = 'block';

            // Positioning
            const rect = e.target.getBoundingClientRect();
            tipsTooltip.style.left = (rect.left + window.scrollX + (rect.width / 2) - 75) + 'px'; // Center tooltip (150px min-width)
            tipsTooltip.style.top = (rect.top + window.scrollY - tipsTooltip.offsetHeight - 10) + 'px';
        });

        input.addEventListener('blur', () => {
            tipsTooltip.style.display = 'none';
        });
    });

    const parseCsInput = (id) => {
        const val = document.getElementById(id).value;
        return val === '' ? null : parseFloat(val);
    };

    if (calculateCustomBtn) {
        calculateCustomBtn.addEventListener('click', () => {
            window._customScenariosData = {};
            ['bear', 'base', 'bull'].forEach(scen => {
                window._customScenariosData[scen] = {
                    rev13: parseCsInput(`cs-rev-1-3-${scen}`),
                    fcfMargin: parseCsInput(`cs-fcf-margin-${scen}`),
                    wacc: parseCsInput(`cs-wacc-${scen}`),
                    exit: parseCsInput(`cs-exit-${scen}`),
                    perp: parseCsInput(`cs-perp-${scen}`),
                    eps: parseCsInput(`cs-eps-${scen}`),
                    pe: parseCsInput(`cs-pe-${scen}`)
                };
            });
            if (customScenariosBtn) customScenariosBtn.classList.add('active-custom');
            if (customScenariosModal) customScenariosModal.style.display = 'none';
            if (typeof updateFairValue === 'function') { updateFairValue(); }
            if (typeof window.triggerRecalculate === 'function') { window.triggerRecalculate(); }
            if (typeof updateScoresDynamic === 'function') { updateScoresDynamic(); }
            saveOverridesDebounced(currentTicker);
        });
    }

    if (resetCustomBtn) {
        resetCustomBtn.addEventListener('click', () => {
            document.querySelectorAll('.cs-input').forEach(inp => inp.value = '');
        });
    }

    if (turnOffCustomBtn) {
        turnOffCustomBtn.addEventListener('click', () => {
            window._customScenariosData = null;
            document.querySelectorAll('.cs-input').forEach(inp => inp.value = '');
            if (customScenariosBtn) customScenariosBtn.classList.remove('active-custom');
            if (customScenariosModal) customScenariosModal.style.display = 'none';
            if (typeof updateFairValue === 'function') { updateFairValue(); }
            if (typeof window.triggerRecalculate === 'function') { window.triggerRecalculate(); }
            if (typeof updateScoresDynamic === 'function') { updateScoresDynamic(); }
            saveOverridesDebounced(currentTicker);
        });
    }
    // --- END CUSTOM SCENARIOS LOGIC ---

    const scenarioBtns = document.querySelectorAll('.scenario-btn:not(.custom-scenarios-btn)');

    scenarioBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            scenarioBtns.forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            const scenario = e.currentTarget.dataset.scenario || 'base';
            _currentScenario = scenario;
            if (globalData) {
                if (globalData.scoring_results && globalData.scoring_results[_currentScenario]) {
                    globalData.good_to_buy_total = globalData.scoring_results[_currentScenario].good_to_buy_total;
                    globalData.buy_breakdown = JSON.parse(JSON.stringify(globalData.scoring_results[_currentScenario].buy_breakdown));
                    currentBuyBreakdown = globalData.buy_breakdown;
                    _originalBuyBreakdown = JSON.parse(JSON.stringify(globalData.buy_breakdown));

                    window.isHighGrowthModel = currentBuyBreakdown && currentBuyBreakdown.some(item => item.metric && item.metric.includes("Rule of 40"));
                    updateScoreUI(globalData.good_to_buy_total, 'buy-score-circle', 'buy-score-fill');

                    const container = document.querySelector('#buy-score-card span.label');
                    if (container) {
                        let badge = container.querySelector('.hg-badge');
                        if (window.isHighGrowthModel) {
                            if (!badge) {
                                badge = document.createElement('span');
                                badge.className = 'hg-badge';
                                badge.style.marginLeft = '10px';
                                badge.style.fontSize = '0.7rem';
                                badge.style.background = 'linear-gradient(90deg, #ec4899, #f43f5e)';
                                badge.style.color = 'white';
                                badge.style.padding = '2px 8px';
                                badge.style.borderRadius = '12px';
                                badge.style.fontWeight = 'bold';
                                badge.style.verticalAlign = 'middle';
                                badge.textContent = '🚀 High-Growth Model';
                                container.appendChild(badge);
                            }
                        } else if (badge) {
                            badge.remove();
                        }
                    }

                    const scoreModal = document.getElementById('score-modal');
                    if (scoreModal && scoreModal.style.display === 'flex') {
                        const titleEl = document.getElementById('score-modal-title');
                        if (titleEl && titleEl.textContent.includes('Good to Buy')) {
                            renderScoreBreakdown('Good to Buy Score Breakdown', globalData.good_to_buy_total, currentBuyBreakdown);
                        }
                    }
                }

                // v310: Re-render estimates table FIRST to dynamically compute the scenario growths
                if (typeof window._renderEstimatesTable === 'function') window._renderEstimatesTable();

                // v290: Auto-update DCF growth input to match scenario

                const newGrowth = window.getDcfGrowthDefault(globalData);
                const g13El = document.getElementById('dcf-growth-1-3');
                if (g13El) {
                    g13El.value = formatCleanInputVal(newGrowth);
                    g13El.dispatchEvent(new Event('input', { bubbles: true }));
                }
                if (window.triggerRecalculate) window.triggerRecalculate();
                if (window._renderProfile) window._renderProfile();
            }
        });
    });

    logoBtn.addEventListener('click', () => {
        document.body.classList.remove('has-searched');
        watchlistView.style.display = 'none';
        dashboard.style.display = 'none';
        currentTicker = null;
        tickerInput.value = '';
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
                const cacheKey = `val_v4_${tUpper}`;
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
        document.body.classList.add('has-searched');
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

        const row = (label, value) => `<div style="display:flex; justify-content:space-between; padding:12px 0; border-bottom:1px solid rgba(255,255,255,0.05);"><span style="color:var(--text-muted);">${label}</span><span style="font-weight:600;">${value}</span></div>`;

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

                let baseFcf = d.fcf || 0;
                let baseRevenue = globalData.revenue || 0;

                if (globalData.historical_data && globalData.historical_data.years) {
                    const histFcf = globalData.historical_data.fcf;
                    const histRev = globalData.historical_data.revenue;
                    const years = globalData.historical_data.years;

                    let lastActualIdx = -1;
                    for (let i = years.length - 1; i >= 0; i--) {
                        if (!String(years[i]).includes('Est')) {
                            lastActualIdx = i;
                            break;
                        }
                    }

                    if (lastActualIdx >= 0) {
                        if (histFcf && histFcf.length > lastActualIdx && histFcf[lastActualIdx] != null) {
                            baseFcf = histFcf[lastActualIdx];
                        }
                        if (histRev && histRev.length > lastActualIdx && histRev[lastActualIdx] != null) {
                            baseRevenue = histRev[lastActualIdx];
                        }
                    }
                }

                const customMarginEl = document.getElementById('dcf-custom-fcf-margin');
                let customMargin = (customMarginEl && customMarginEl.value !== '') ? parseLocaleFloat(customMarginEl.value) : null;

                let cs = window._customScenariosData && window._customScenariosData[_currentScenario] ? window._customScenariosData[_currentScenario] : null;
                if (cs && cs.fcfMargin !== null) {
                    customMargin = cs.fcfMargin;
                }

                let startingFcfMargin = 0.10;
                if (customMargin !== null && !isNaN(customMargin)) {
                    startingFcfMargin = customMargin / 100;
                } else if (baseRevenue > 0) {
                    startingFcfMargin = baseFcf / baseRevenue;
                }
                const customMarginGrowthEl = document.getElementById('dcf-custom-margin-growth');
                const customMarginGrowth = (customMarginGrowthEl && customMarginGrowthEl.value !== '') ? parseLocaleFloat(customMarginGrowthEl.value) / 100 : 0.002;

                let tableHTML = `<div class="table-responsive"><table class="premium-data-table">
                                        <tr style="border-bottom:1px solid rgba(255,255,255,0.2);">
                                            <th style="text-align:left; padding:8px 0; color:white;">Year</th>
                                            <th style="text-align:right; padding:8px 0; color:white;">Projected FCF</th>
                                            <th style="text-align:right; padding:8px 0; color:white;">FCF Margin</th>
                                        </tr>`;
                fcfYears.forEach((val, i) => {
                    const yearMargin = startingFcfMargin + ((i + 1) * customMarginGrowth);
                    tableHTML += `<tr>
                                        <td style="padding:6px 0; color:white;">Year ${i + 1}</td>
                                        <td style="text-align:right; color:white;">${fmtBig(val)}</td>
                                        <td style="text-align:right; color:var(--accent); font-weight:600;">${fmtPct(yearMargin)}</td>
                                      </tr>`;
                });
                tableHTML += `</table></div>`;

                const tvLabel = method === 'perpetual' ? `Terminal Value (${fmtPct(dataObj.perpetual_growth_rate)} Growth)` : `Terminal Value (${dataObj.exit_multiple}x Multiple)`;

                let matrixHTML = '';
                if (method === 'perpetual' && sensMatrix.length > 0) {
                    matrixHTML = `<div style="margin-top: 25px;">
                            <h4 style="margin-bottom:15px; font-size:1rem; text-transform:uppercase; letter-spacing:1px; color:white; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:5px;">DCF Sensitivity Matrix</h4>
                            <div style="overflow-x:auto;">
                            <table class="premium-data-table">`;

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
            title.style.whiteSpace = 'nowrap';
            title.style.overflow = 'hidden';
            title.style.textOverflow = 'ellipsis';
            title.style.fontSize = 'clamp(0.85rem, 3.5vw, 1.25rem)';
            title.style.lineHeight = '1.3';
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

            // --- Custom Weights Logic ---
            const ticker = globalData.ticker;
            const overrides = cachedOverrides[ticker]?.inputs || {};
            const customW = {};
            let hasCustomW = false;
            ['w-pe', 'w-pfcf', 'w-ps', 'w-pb', 'w-evebitda'].forEach(id => {
                if (overrides[id] !== undefined) {
                    const k = id.split('-')[1].toUpperCase().replace('EVEBITDA', 'EV_EBITDA');
                    customW[k] = overrides[id] / 100;
                    hasCustomW = true;
                }
            });
            const weightsToUse = hasCustomW ? customW : defaultWeights;

            // Active metric keys for this sector
            const activeKeys = Object.keys(weightsToUse).filter(k => (weightsToUse[k] || 0) > 0);

            // Label map
            const LABEL = { PE: 'FWD P/E', PFCF: 'P/FCF', PS: 'FWD EV/Sales', PB: 'P/B', EV_EBITDA: 'FWD EV/EBITDA', P_FFO: 'FWD P/FFO', P_AFFO: 'FWD P/AFFO' };
            const peerKeyMap = { PE: 'forward_pe', PFCF: 'pfcf_ratio', PS: 'forward_ev_sales', PB: 'price_to_book', EV_EBITDA: 'forward_ev_ebitda', P_FFO: 'forward_pe', P_AFFO: 'pfcf_ratio' };

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
                    <table class="premium-data-table" style="font-size:0.75rem;">
                        <thead>
                            <tr style="border-bottom:1px solid rgba(255,255,255,0.15);">
                                <th style="text-align:left; padding:4px 2px; color:white; white-space:nowrap;">Ticker</th>
                                ${activeKeys.map(k => `<th style="text-align:right; padding:4px 2px; color:white; white-space:nowrap;">${LABEL[k] || k}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            <!-- Target Company Row -->
                            <tr style="border-bottom:1px solid rgba(255,255,255,0.1); background: rgba(40, 199, 111, 0.05);">
                                <td style="padding:4px 2px; color:#28c76f; font-weight:700; white-space:nowrap;">${(globalData.ticker || 'TARGET').toUpperCase()}</td>
                                ${activeKeys.map(k => {
                    let val = null;
                    const dynEpsG = r.dynamic_eps_growth != null ? r.dynamic_eps_growth : ((globalData && globalData.computed_eps_growth != null) ? globalData.computed_eps_growth : (globalData.company_profile?.earnings_growth || 0));
                    const dynRevG = r.dynamic_rev_growth != null ? r.dynamic_rev_growth : ((globalData && globalData.computed_dcf_growth != null) ? globalData.computed_dcf_growth : (globalData.company_profile?.revenue_growth || 0));

                    console.log(`[RelModal] Scenario=${_currentScenario} | dyn_eps_g=${dynEpsG} | dyn_rev_g=${dynRevG}`);

                    // 1. FWD P/E
                    const dynFwdEps = r.dynamic_company_eps;
                    const impliedPe = dynFwdEps > 0 ? (_realApiPrice / dynFwdEps) : (globalData.company_profile && (globalData.company_profile.fwd_pe || globalData.company_profile.forward_pe));

                    // 2. FWD EV/EBITDA
                    const dynEbitda = (globalData.ebitda || 0) * (1 + dynEpsG);
                    const impliedEvEbitda = dynEbitda > 0 ? ((globalData.company_profile?.market_cap || 0) + (globalData.total_debt || 0) - (globalData.total_cash || 0)) / dynEbitda : null;

                    // 3. FWD EV/Sales
                    const company_shares = (globalData.company_profile && globalData.company_profile.shares_outstanding) || 1;
                    const rev = r.dynamic_company_sales_share ? (r.dynamic_company_sales_share * company_shares) : ((globalData.revenue || 0) * (1 + dynRevG));
                    const impliedPs = rev > 0 ? ((globalData.company_profile?.market_cap || 0) + (globalData.total_debt || 0) - (globalData.total_cash || 0)) / rev : null;

                    if (k === 'PE' || k === 'P_FFO') {
                        val = impliedPe;
                    }
                    else if (k === 'PS') {
                        val = impliedPs;
                        if (val == null) val = (globalData.company_profile && (globalData.company_profile.fwd_ps || globalData.company_profile.forward_ev_sales));
                    }
                    else if (k === 'PB') {
                        val = (globalData.company_profile && globalData.company_profile.price_to_book);
                    }
                    else if (k === 'EV_EBITDA') {
                        val = impliedEvEbitda;
                        if (val == null) val = globalData.company_profile && (globalData.company_profile.forward_ev_ebitda || globalData.company_profile.ev_to_ebitda);
                    }
                    else if (k === 'PFCF' || k === 'P_AFFO') {
                        const pfcf_ttm = globalData.company_profile && globalData.company_profile.pfcf_ratio || 0;
                        val = pfcf_ttm > 0 ? pfcf_ttm / (1 + dynEpsG) : null;
                    }

                    return `<td style="text-align:right; padding:4px 2px; color:#28c76f; font-weight:700; white-space:nowrap;">${val != null ? val.toFixed(1) + 'x' : '—'}</td>`;
                }).join('')}
                            </tr>
                            
                            <!-- Peers Rows -->
                            ${peers.map(p => `
                                <tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
                                    <td style="padding:4px 2px; color:white; font-weight:600; white-space:nowrap;">${p.ticker}</td>
                                    ${activeKeys.map(k => {
                    const dk = peerKeyMap[k];
                    const val = dk ? p[dk] : null;
                    return `<td style="text-align:right; padding:4px 2px; color:var(--text-main); white-space:nowrap;">${val != null && val !== 0 ? val.toFixed(1) + 'x' : '—'}</td>`;
                }).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr style="border-top:1px solid rgba(255,255,255,0.15);">
                                <td style="padding:4px 2px; color:white; font-weight:700; white-space:nowrap;">Median</td>
                                ${activeKeys.map(k => {
                    let medKey = k;
                    if (k === 'P_FFO') medKey = 'PE';
                    if (k === 'P_AFFO') medKey = 'PFCF';
                    const v = dynamicMedians[medKey] ?? r['median_peer_' + medKey.toLowerCase()];
                    return `<td style="text-align:right; padding:4px 2px; color:white; font-weight:700; white-space:nowrap;">${v != null ? v.toFixed(1) + 'x' : '—'}</td>`;
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
                const prof = globalData.company_profile || {};

                const eps = r.dynamic_company_eps != null ? r.dynamic_company_eps : ((r.company_fwd_eps || 0) > 0 ? r.company_fwd_eps : (r.company_eps || 0));
                const fcfS = (r.company_fcf_share || 0);

                const explicit_fwd_ps = prof.fwd_ps;
                const salesS = r.dynamic_company_sales_share != null ? r.dynamic_company_sales_share : (explicit_fwd_ps > 0 ? (_realApiPrice / explicit_fwd_ps) : (r.company_sales_share || 0));

                const bookS = r.company_book_share || 0;
                const dynEpsG = r.dynamic_eps_growth != null ? r.dynamic_eps_growth : ((globalData && globalData.computed_eps_growth != null) ? globalData.computed_eps_growth : (prof.earnings_growth || 0));
                const ebitda = (globalData.ebitda || 0) * (1 + dynEpsG);

                const debt = globalData.total_debt || 0;
                const cash = globalData.total_cash || 0;
                const shares = prof.shares_outstanding || 1;

                if (key === 'PE' || key === 'P_FFO') return eps * bench;
                if (key === 'PFCF' || key === 'P_AFFO') return fcfS * bench;
                if (key === 'PB') return bookS * bench;
                if (key === 'EV_EBITDA') {
                    const ev = ebitda * bench;
                    return shares > 0 ? (ev - debt + cash) / shares : 0;
                }
                if (key === 'PS') {
                    let rev = salesS * shares;
                    if (!rev || rev === 0) {
                        const dynRevG = r.dynamic_rev_growth != null ? r.dynamic_rev_growth : ((globalData && globalData.computed_dcf_growth != null) ? globalData.computed_dcf_growth : (prof.revenue_growth || 0));
                        rev = (globalData.revenue || 0) * (1 + dynRevG);
                    }
                    const ev = rev * bench;
                    return shares > 0 ? (ev - debt + cash) / shares : 0;
                }
                return 0;
            };

            let breakdownRows = '';
            activeKeys.forEach(k => {
                const bench = getBenchmark(k);
                const implied = getImplied(k, bench);
                const w = weightsToUse[k] || 0;
                const safeImpl = implied > 0 ? implied : 0;
                const implColor = safeImpl > 0 ? 'white' : 'var(--text-muted)';
                breakdownRows += `
                        <tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
                            <td style="padding:4px 2px; color:var(--text-main); white-space:nowrap;">${LABEL[k]}</td>
                            <td style="text-align:right; padding:4px 2px; color:var(--text-main); white-space:nowrap;">${(bench || 0).toFixed(1)}x</td>
                            <td style="text-align:right; padding:4px 2px; color:${implColor}; font-weight:600; white-space:nowrap;">${safeImpl > 0 ? '$' + fmt(safeImpl) : 'N/A'}</td>
                            <td style="text-align:right; padding:4px 2px; color:var(--accent); font-weight:700; white-space:nowrap;" class="rel-weight-cell" data-key="${k}">${(w * 100).toFixed(0)}%</td>
                        </tr>`;
            });

            // Compute initial weighted FV for the modal display
            let _initSum = 0, _initTot = 0;
            activeKeys.forEach(k => {
                const b = getBenchmark(k);
                const impl = getImplied(k, b);
                const w = weightsToUse[k] || 0;
                if (w > 0 && impl > 0) { _initSum += impl * w; _initTot += w; }
            });
            const modalFV = _initTot > 0 ? _initSum / _initTot : 0;
            const modalFVColor = modalFV > (globalData.current_price || 0) ? 'var(--accent)' : 'var(--danger)';

            html = `
                    ${peerTableHTML}

                    <h4 style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;">Implied Values & Weights</h4>
                    <table style="width:100%; border-collapse:collapse; font-size:0.65rem; margin-bottom:1rem;">
                        <thead>
                            <tr style="border-bottom:1px solid rgba(255,255,255,0.15);">
                                <th style="text-align:left; padding:4px 2px; color:white; white-space:nowrap;">Metric</th>
                                <th style="text-align:right; padding:4px 2px; color:white; white-space:nowrap;">Benchmark</th>
                                <th style="text-align:right; padding:4px 2px; color:white; white-space:nowrap;">Implied FV</th>
                                <th style="text-align:right; padding:4px 2px; color:white; white-space:nowrap;">Weight</th>
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
            const prof = globalData.company_profile || {};
            title.textContent = '📊 Forward Multiple — Data Transparency';
            const epsLabel = p.valuation_eps !== p.trailing_eps ? 'EPS Base (Normalized)' : 'Trailing EPS (GAAP)';
            const dynMult = p.dynamic_mult != null ? (Number.isInteger(p.dynamic_mult) ? p.dynamic_mult : p.dynamic_mult.toFixed(2)) : 20;
            const targetPrice = p.dynamic_fwd_price != null ? p.dynamic_fwd_price : (p.fwd_eps != null ? p.fwd_eps * dynMult : null);
            html = row(epsLabel, '$' + fmt(p.valuation_eps || p.trailing_eps))
                + row('Growth Estimate', fmtPct(p.dynamic_growth != null ? p.dynamic_growth : p.eps_growth_estimated))
                + row('Forward EPS (3Y Projection)', '$' + fmt(p.dynamic_fwd_eps != null ? p.dynamic_fwd_eps : p.fwd_eps))
                + row('5Y Avg P/E', prof.historic_pe ? prof.historic_pe.toFixed(2) + 'x' : 'N/A')
                + (targetPrice != null ? row(`3Y Target Price (PE ${dynMult})`, '$' + fmt(targetPrice)) : '')
                + row(`Return Rate (Discount)`, p.dynamic_discount != null ? fmtPct(p.dynamic_discount) : '15.0%')
                + row(`Present Fair Value`, '$' + fmt(p.dynamic_fv != null ? p.dynamic_fv : p.fair_value_pe_20));
        } else if (model === 'peg' && currentFormulaData.peg) {
            const g = currentFormulaData.peg;
            const prof = globalData.company_profile || {};
            title.textContent = '📊 PEG Valuation — Data Transparency';
            const periodLabel = g.eps_growth_period || '2Y EPS CAGR';
            const displayPe = g.dynamic_pe != null ? g.dynamic_pe : g.current_pe;
            const epsTypeLabel = prof.peg_eps_type === 'GAAP' ? '(GAAP)' : '(Non-GAAP)';
            
            const pegSrcElem = document.getElementById('peg-eps-source');
            const pegSrcMode = pegSrcElem ? pegSrcElem.value : 'analyst';
            let peLabel = `P/E TTM ${epsTypeLabel}`;
            if (pegSrcMode === '5ycagr' || pegSrcMode === 'analyst') {
                peLabel = 'P/E FWD';
            }

            html = row(peLabel, displayPe ? displayPe.toFixed(2) + 'x' : 'N/A')
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

        // v315: Synchronize Good To Buy Modal values with dynamic frontend calculations
        if (title.includes('Good to Buy') && typeof globalData !== 'undefined' && globalData) {
            let dynFwdEps = globalData.company_profile ? globalData.company_profile.fwd_eps : null;
            if (globalData.eps_estimates) {
                const eEsts = globalData.eps_estimates.filter(e => e && e.status !== 'reported' && e.period && (e.period.includes('Year') || e.period.includes('FY') || e.period.endsWith('y')));
                if (eEsts.length >= 1) {
                    if (window._currentScenario === 'bear') dynFwdEps = eEsts[0].low ?? eEsts[0].avg;
                    else if (window._currentScenario === 'bull') dynFwdEps = eEsts[0].high ?? eEsts[0].avg;
                    else dynFwdEps = eEsts[0].avg;
                }
            }
            const currentPrice = globalData.current_price || (globalData.company_profile ? globalData.company_profile.price : null);
            const dynFwdPe = (dynFwdEps && dynFwdEps > 0 && currentPrice) ? currentPrice / dynFwdEps : null;

            breakdown.forEach(item => {
                if (item.metric.includes('P/E Ratio') && item.metric.includes('Fwd') && dynFwdPe) {
                    item.value = dynFwdPe.toFixed(2) + 'x';
                } else if (item.metric.includes('PEG Ratio (Fwd)')) {
                    if (typeof currentFormulaData !== 'undefined' && currentFormulaData && currentFormulaData.peg && currentFormulaData.peg.dynamic_peg) {
                        item.value = currentFormulaData.peg.dynamic_peg.toFixed(2) + 'x';
                    }
                } else if (item.metric.includes('EPS Growth (Fwd)')) {
                    if (globalData.computed_eps_growth != null && !isNaN(globalData.computed_eps_growth)) {
                        item.value = (globalData.computed_eps_growth * 100).toFixed(1) + '%';
                    }
                }
            });
        }

        let totalMax = 0;
        breakdown.forEach(item => totalMax += item.max_points || 0);
        const scoreVal = totalScore != null ? totalScore : '?';

        // Build header - 3-column grid to center the total and align with X
        const displayTitle = title.replace(' Breakdown', '');
        let html = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding-bottom:10px; gap:15px; flex-wrap:nowrap; border-bottom:1px solid rgba(255,255,255,0.1);">
                <h3 style="margin:0; font-size:1.05rem; color:white; font-weight:800; white-space:nowrap; border-bottom:none !important; line-height:1.3rem;">${displayTitle}</h3>
                
                <div style="display:flex; align-items:baseline; gap:6px; flex-shrink:0; line-height:1.3rem;">
                    <span style="font-size:0.75rem; color:var(--text-muted); font-weight:600; text-transform:uppercase;">Total:</span>
                    <span style="font-size:1.3rem; font-weight:900; color:white;">${scoreVal}/${totalMax}</span>
                </div>
            </div>
        `;

        // Build rows - Label on left, Value and Score on right
        breakdown.forEach(item => {
            let label = (item.metric || item.name || 'Unknown Metric');
            const originalMetric = label;
            label = label.replace(/\s*\(.*\)/, '').trim();

            if (originalMetric.includes('1Y Fwd') || originalMetric.includes('Fwd') || originalMetric.includes('FWD')) {
                if (label.includes('P/E Ratio')) label = 'P/E FWD';
                else if (label.includes('P/S Ratio')) label = 'P/S FWD';
                else if (label.includes('EV/EBITDA') || label.includes('EV / EBITDA')) label = 'EV/EBITDA FWD';
                else if (label.includes('Revenue Growth')) label = 'Revenue Growth FWD';
                else if (label.includes('EPS Growth') || label.includes('AFFO/EPS Growth')) label = 'EPS Growth FWD';
                else if (label.includes('Dividend Yield')) label = 'Dividend Yield FWD';
                else if (label.includes('PEG Ratio')) label = 'PEG FWD';
                else if (label.includes('P/AFFO')) label = 'P/AFFO FWD';
            }

            const pts = (item.points_awarded !== undefined) ? item.points_awarded : (item.points || 0);
            const maxPts = item.max_points || 0;
            const pct = maxPts > 0 ? (pts / maxPts) : 0;

            // Dot color
            let dotColor = 'var(--danger)';
            let ptsColor = 'var(--danger)';
            if (pct >= 0.99) { dotColor = 'var(--accent)'; ptsColor = 'var(--accent)'; }
            else if (pct >= 0.4) { dotColor = '#fbbf24'; ptsColor = '#fbbf24'; }

            let valStr = String(item.value || 'N/A');
            let suffix = '';
            if (valStr.endsWith('%')) { suffix = '%'; valStr = valStr.slice(0, -1); }
            else if (valStr.toLowerCase().endsWith('x')) { suffix = 'x'; valStr = valStr.slice(0, -1); }

            const valueHtml = suffix
                ? `<div style="font-weight: 700; font-size: 0.9rem; color: rgba(255,255,255,0.85); font-family: monospace; white-space: nowrap;">${valStr}<span style="font-size: 0.8em; color: rgba(255,255,255,0.7); margin-left: 2px;">${suffix}</span></div>`
                : `<div style="font-weight: 700; font-size: 0.9rem; color: rgba(255,255,255,0.85); font-family: monospace; white-space: nowrap;">${valStr}</div>`;

            html += `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.03); gap: 15px;">
                    <div style="font-weight: 600; font-size: 0.85rem; color: white; line-height: 1.3;">${label}</div>
                    
                    <div style="display: flex; align-items: center; gap: 15px;">
                        ${valueHtml}

                        <div style="display: flex; align-items: center; gap: 8px; justify-content: flex-end; width: 60px;">
                            <span style="width: 6px; height: 6px; border-radius: 50%; background: ${dotColor}; display: inline-block; flex-shrink: 0;"></span>
                            <div style="font-weight: 800; font-size: 0.85rem; color: ${ptsColor}; font-family: 'Outfit', sans-serif; min-width: 35px; text-align: right;">${pts}/${maxPts}</div>
                        </div>
                    </div>
                </div>
            `;
        });

        if (titleEl) titleEl.textContent = '';
        body.innerHTML = html;
        modal.style.display = 'flex';
    };

    // ── Beneish M-Score Breakdown Modal ──────────────────────
    function renderBeneishBreakdown(beneishData) {
        const modal = document.getElementById('score-modal');
        const body = document.getElementById('score-modal-body-content');
        const titleEl = document.getElementById('score-modal-title');
        if (!modal || !body) return;

        if (!beneishData || beneishData.m_score == null || !beneishData.breakdown || beneishData.breakdown.length === 0) {
            if (titleEl) titleEl.textContent = 'Beneish M-Score';
            body.innerHTML = '<p style="color:var(--text-muted);">No Beneish data available for this ticker.</p>';
            modal.style.display = 'flex';
            return;
        }

        const scoreVal = beneishData.m_score;
        let html = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding-bottom:10px; gap:15px; border-bottom:1px solid rgba(255,255,255,0.1);">
                <h3 style="margin:0; font-size:1.05rem; color:white; font-weight:800; line-height:1.3rem;">Beneish M-Score</h3>
                <div style="display:flex; align-items:baseline; gap:6px; line-height:1.3rem;">
                    <span style="font-size:0.75rem; color:var(--text-muted); font-weight:600; text-transform:uppercase;">Total:</span>
                    <span style="font-size:1.3rem; font-weight:900; color:white;">${scoreVal}</span>
                </div>
            </div>
            <div style="margin-bottom: 15px; font-size: 0.85rem; color: var(--text-muted);">
                A score less than <b>-1.78</b> suggests a low risk of accounting manipulation. Higher scores indicate increased risk.
            </div>
        `;

        beneishData.breakdown.forEach(item => {
            const label = item.metric || 'Unknown';
            const passed = item.status === 'pass';
            const dotColor = passed ? 'var(--accent)' : (item.status === 'fail' ? 'var(--danger)' : 'var(--text-muted)');

            html += `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.05); gap: 15px;">
                    <div style="font-weight: 600; font-size: 0.9rem; color: white; line-height: 1.3;">${label}</div>

                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="font-weight: 700; font-size: 0.9rem; color: rgba(255,255,255,0.85); font-family: monospace; white-space: nowrap;">
                            ${item.value !== null ? item.value : 'N/A'}
                        </div>
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: ${dotColor}; display: inline-block; flex-shrink: 0;"></span>
                    </div>
                </div>
            `;
        });

        if (titleEl) titleEl.textContent = '';
        body.innerHTML = html;
        modal.style.display = 'flex';
    }

    // ── News Modal ──────────────────────
    window.openNewsModalByIndex = function(index) {
        try {
            if (!globalData || !globalData.latest_news || !globalData.latest_news[index]) {
                return;
            }
            const news = globalData.latest_news[index];

            // create modal container if not exists
            let modal = document.getElementById('news-modal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'news-modal';
                modal.style.position = 'fixed';
                modal.style.top = '0';
                modal.style.left = '0';
                modal.style.width = '100vw';
                modal.style.height = '100vh';
                modal.style.backgroundColor = 'rgba(0, 0, 0, 0.75)';
                modal.style.backdropFilter = 'blur(5px)';
                modal.style.zIndex = '999999';
                modal.style.display = 'flex';
                modal.style.alignItems = 'center';
                modal.style.justifyContent = 'center';
                modal.style.opacity = '0';
                modal.style.transition = 'opacity 0.2s ease-out';

                modal.onclick = function(e) {
                    if (e.target === modal) {
                        window.closeNewsModal();
                    }
                };
                document.body.appendChild(modal);
            }

            window.closeNewsModal = function() {
                const m = document.getElementById('news-modal');
                if (m) {
                    m.style.opacity = '0';
                    setTimeout(() => { m.style.display = 'none'; }, 200);
                }
            };

            modal.innerHTML = `
                <div style="background: var(--bg-surface); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; width: 90%; max-width: 500px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); position: relative; font-family: 'Outfit', sans-serif;">
                    <button onclick="window.closeNewsModal()" style="position: absolute; top: 12px; right: 12px; background: none; border: none; color: rgba(255,255,255,0.5); font-size: 1.2rem; cursor: pointer; padding: 4px;">&times;</button>

                    <div style="margin-bottom: 15px; display: inline-block;">
                        <span style="background: rgba(56, 189, 248, 0.1); color: #38bdf8; font-size: 0.7rem; padding: 4px 8px; border-radius: 6px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">${news.publisher || 'News'}</span>
                    </div>

                    <h2 style="font-size: 1.2rem; color: #fff; line-height: 1.4; margin-top: 0; margin-bottom: 16px; font-weight: 700;">${news.title}</h2>

                    ${news.summary ? `<div style="background: rgba(255,255,255,0.03); border-left: 3px solid #4ade80; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;">
                        <p style="color: rgba(255,255,255,0.85); font-size: 0.9rem; line-height: 1.6; margin: 0; font-style: italic;">"${news.summary}"</p>
                    </div>` : ''}

                    ${news.link ? `<div style="text-align: right;">
                        <a href="${news.link}" target="_blank" rel="noopener noreferrer" style="display: inline-flex; align-items: center; gap: 8px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; text-decoration: none; padding: 10px 16px; border-radius: 8px; font-weight: 600; font-size: 0.9rem; transition: all 0.2s;">
                            Read Full Article <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                        </a>
                    </div>` : ''}
                </div>
            `;

            modal.style.display = 'flex';
            // Trigger reflow
            modal.offsetHeight;
            modal.style.opacity = '1';

        } catch (err) {
            console.error("Error parsing news data", err);
        }
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
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding-bottom:10px; gap:15px; border-bottom:1px solid rgba(255,255,255,0.1);">
                <h3 style="margin:0; font-size:1.05rem; color:white; font-weight:800; line-height:1.3rem;">Piotroski F-Score</h3>
                <div style="display:flex; align-items:baseline; gap:6px; line-height:1.3rem;">
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
                html += `<div style="margin-top: 15px; margin-bottom: 5px; font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">${group}</div>`;
            }

            const label = item.criterion || item.name || 'Unknown';
            const passed = item.passed;
            const dotColor = passed === true ? 'var(--accent)' : (passed === false ? 'var(--danger)' : 'var(--text-muted)');
            const statusText = passed === true ? 'Pass' : (passed === false ? 'Fail' : 'N/A');
            const statusColor = passed === true ? 'var(--accent)' : (passed === false ? 'var(--danger)' : 'var(--text-muted)');

            html += `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.03); gap: 15px;">
                    <div style="font-weight: 600; font-size: 0.85rem; color: white; line-height: 1.3;">${label}</div>

                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="font-weight: 700; font-size: 0.85rem; color: rgba(255,255,255,0.85); font-family: monospace; white-space: nowrap;">
                            ${item.value || 'N/A'}
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px; width: 45px; justify-content: flex-end;">
                            <div style="font-weight: 800; font-size: 0.8rem; color: ${statusColor}; text-transform: uppercase;">${statusText}</div>
                            <span style="width: 6px; height: 6px; border-radius: 50%; background: ${dotColor}; display: inline-block; flex-shrink: 0;"></span>
                        </div>
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


    // PWA Install Logic
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        const installBtn = document.getElementById('install-app-btn');
        if (installBtn) {
            installBtn.style.display = 'block';
        }
    });

    const installBtn = document.getElementById('install-app-btn');
    if (installBtn) {
        installBtn.addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                if (outcome === 'accepted') {
                    installBtn.style.display = 'none';
                }
                deferredPrompt = null;
            }
        });
    }

});
