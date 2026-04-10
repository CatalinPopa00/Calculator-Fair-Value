def clean_percent(val):
    if val is None: return 0.0
    if isinstance(val, str):
        val = val.replace('%', '').replace('x', '').replace('$', '').replace(',', '')
    try:
        f_val = float(val)
        # Standardize decimal (0.05 -> 5%) before calculation and display.
        # v43: Threshold increased to 10.0 (1000%) to handle hyper-growth like SMCI (1.23 -> 123%).
        if 0 < abs(f_val) < 10.0:
            return f_val * 100.0
        return f_val
    except:
        return 0.0
def calculate_scoring_reform(valuation_data, metrics):
    sector = metrics.get('sector', 'Technology')
    industry = str(metrics.get('industry', '')).lower()
    
    # Check if this is a traditional bank/lender or a general financial service (like SPGI/MSCI)
    is_bank = 'bank' in industry or 'credit services' in industry or 'savings' in industry
    is_financial = 'financial' in sector.lower()
    is_reit = 'real estate' in sector.lower() or 'reit' in sector.lower()

    h_score = 0
    h_breakdown = []
    b_score = 0
    b_breakdown = []

    def format_val(value, is_ratio=True):
        if value is None: return "0.00"
        if is_ratio == "raw": return str(value)
        if is_ratio: return f"{value:.2f}x"
        return f"{value:.1f}%"

    def add_h(metric, value, pts, max_pts, is_ratio=True):
        nonlocal h_score
        pts = min(pts, max_pts)  # Guard: never exceed max
        h_score += pts
        h_breakdown.append({
            "metric": metric,
            "value": format_val(value, is_ratio),
            "points_awarded": int(pts),
            "max_points": int(max_pts)
        })

    def add_b(metric, value, pts, max_pts, is_ratio=True):
        nonlocal b_score
        pts = min(pts, max_pts)  # Guard: never exceed max
        b_score += pts
        b_breakdown.append({
            "metric": metric,
            "value": format_val(value, is_ratio),
            "points_awarded": int(pts),
            "max_points": int(max_pts)
        })

    # Prepare standard metrics with 0.05 -> 5% normalization
    mos = clean_percent(valuation_data.get('margin_of_safety'))
    rev_g = clean_percent(metrics.get('revenue_growth'))
    peg = clean_percent(metrics.get('peg_ratio')) 
    
    def clean_ratio(val):
        if val is None: return 0.0
        if isinstance(val, str):
            val = val.replace('%', '').replace('x', '').replace('$', '').replace(',', '')
        try: return float(val)
        except: return 0.0

    # USER-DRIVEN DATA MAPPING: TRAILING PE ONLY (FORBIDDEN FORWARD PE)
    pe = clean_ratio(metrics.get('trailing_pe') or metrics.get('pe_ratio'))

    if is_financial and is_bank:
        # --- ȘABLONUL 2: FINANCIALS ---
        # HEALTH (100 pct)
        de = clean_ratio(metrics.get('debt_to_equity'))
        pts = 20 if de < 0.8 else (10 if de <= 1.5 else 0)
        add_h("Debt-to-Equity", de, pts, 20, True)

        nim = clean_percent(metrics.get('nim'))
        pts = 15 if nim > 3.0 else (7.5 if nim >= 1.5 else 0)
        add_h("Net Interest Margin", nim, pts, 15, False)

        cet1 = clean_percent(metrics.get('cet1_ratio'))
        pts = 15 if cet1 > 12 else (7.5 if cet1 >= 9 else 0)
        add_h("CET1 Ratio", cet1, pts, 15, False)

        roe = clean_percent(metrics.get('roe'))
        pts = 15 if roe > 15 else (7.5 if roe >= 8 else 0)
        add_h("ROE", roe, pts, 15, False)

        roa = clean_percent(metrics.get('roa'))
        pts = 20 if roa > 1.5 else (10 if roa >= 0.5 else 0)
        add_h("ROA", roa, pts, 20, False)

        bvps = clean_percent(metrics.get('bvps_growth'))
        pts = 15 if bvps > 8 else (7.5 if bvps >= 3 else 0)
        add_h("BVPS Growth", bvps, pts, 15, False)

        # BUY (100 pct)
        pts = 30 if mos > 20 else (15 if mos >= 0 else 0)
        add_b("Margin of Safety", mos, pts, 30, False)

        f_peg = clean_ratio(metrics.get('peg_ratio'))
        pts = 15 if (f_peg > 0 and f_peg < 1.0) else (7.5 if (f_peg > 0 and f_peg <= 1.5) else 0)
        add_b("PEG Ratio", f_peg, pts, 15, True)

        # P/E Ratio (HYBRID BLENDED SCORE - 15 pct max)
        pe_5y = clean_ratio(metrics.get('pe_historic'))
        # Part A: Absolute (7.5 pct)
        pts_abs = 7.5 if (pe > 0 and pe < 10.0) else (3.75 if (pe > 0 and pe <= 15.0) else 0)
        # Part B: Relative to 5Y Avg (7.5 pct)
        pts_rel = 0
        if pe > 0 and pe_5y > 0:
            pe_diff_pct = ((pe - pe_5y) / pe_5y) * 100
            pts_rel = 7.5 if pe_diff_pct < -15 else (3.75 if abs(pe_diff_pct) <= 15 else 0)
        pts = pts_abs + pts_rel
        add_b("P/E Ratio", pe, pts, 15, True)

        pb = clean_ratio(metrics.get('price_to_book'))
        pts = 15 if (pb > 0 and pb < 1.2) else (7.5 if (pb > 0 and pb <= 2.0) else 0)
        add_b("Price-to-Book", pb, pts, 15, True)

        div_y = clean_percent(metrics.get('dividend_yield'))
        pts = 15 if div_y > 4 else (7.5 if div_y >= 2 else 0)
        add_b("Dividend Yield", div_y, pts, 15, False)

        rev_g_3y = clean_percent(metrics.get('next_3y_rev_growth'))
        pts = 10 if rev_g_3y > 10 else (5 if rev_g_3y >= 5 else 0)
        add_b("Next 3Y Rev Growth", rev_g_3y, pts, 10, False)

    elif is_reit:
        # --- ȘABLONUL 3: REAL ESTATE (REITS) ---
        # HEALTH (100 pct)
        de = clean_ratio(metrics.get('debt_to_equity'))
        pts = 20 if de < 0.8 else (10 if de <= 1.5 else 0)
        add_h("Debt-to-Equity", de, pts, 20, True)

        ic = clean_ratio(metrics.get('interest_coverage'))
        pts = 15 if ic > 3.0 else (7.5 if ic >= 1.5 else 0)
        add_h("Interest Coverage", ic, pts, 15, True)

        nd_ebitda = clean_ratio(metrics.get('debt_to_ebitda'))
        pts = 15 if (nd_ebitda > 0 and nd_ebitda < 5.5) else (7.5 if (nd_ebitda > 0 and nd_ebitda <= 7.0) else 0)
        add_h("Debt-to-EBITDA", nd_ebitda, pts, 15, True)

        affo_m = clean_percent(metrics.get('affo_margin'))
        pts = 15 if affo_m > 50 else (7.5 if affo_m >= 30 else 0)
        add_h("AFFO Margin", affo_m, pts, 15, False)

        roic = clean_percent(metrics.get('roic'))
        pts = 20 if roic > 8 else (10 if roic >= 4 else 0)
        add_h("ROIC", roic, pts, 20, False)

        affo_g = clean_percent(metrics.get('affo_growth'))
        pts = 15 if affo_g > 5 else (7.5 if affo_g >= 2 else 0)
        add_h("AFFO Growth", affo_g, pts, 15, False)

        # BUY (100 pct)
        pts = 30 if mos > 20 else (15 if mos >= 0 else 0)
        add_b("Margin of Safety", mos, pts, 30, False)

        p_affo = clean_ratio(metrics.get('price_to_affo'))
        pts = 20 if (p_affo > 0 and p_affo < 15.0) else (10 if (p_affo > 0 and p_affo <= 20.0) else 0)
        add_b("P/AFFO", p_affo, pts, 20, True)

        div_y = clean_percent(metrics.get('dividend_yield'))
        pts = 15 if div_y > 5 else (7.5 if div_y >= 3 else 0)
        add_b("Dividend Yield", div_y, pts, 15, False)

        fcf_y = clean_percent(metrics.get('fcf_yield'))
        pts = 15 if fcf_y > 10 else (7.5 if fcf_y >= 5 else 0)
        add_b("FCF Yield", fcf_y, pts, 15, False)

        affo_g = clean_percent(metrics.get('affo_growth'))
        pts = 10 if affo_g > 5 else (5 if affo_g >= 2 else 0)
        add_b("AFFO Growth", affo_g, pts, 10, False)

        rev_g = clean_percent(metrics.get('revenue_growth'))
        pts = 10 if rev_g > 10 else (5 if rev_g >= 5 else 0)
        add_b("Rev Growth", rev_g, pts, 10, False)

    else:
        # --- ȘABLONUL 1: DEFAULT ---
        # HEALTH (100 pct)
        de = clean_ratio(metrics.get('debt_to_equity'))
        pts = 20 if de < 0.8 else (10 if de <= 1.5 else 0)
        add_h("Debt-to-Equity", de, pts, 20, True)

        ic = clean_ratio(metrics.get('interest_coverage'))
        pts = 15 if ic > 10 else (7.5 if ic >= 3 else 0)
        add_h("Interest Coverage", ic, pts, 15, True)

        cr = clean_ratio(metrics.get('current_ratio'))
        pts = 15 if cr > 1.2 else (7.5 if cr >= 0.8 else 0)
        add_h("Current Ratio", cr, pts, 15, True)

        ebit_m = clean_percent(metrics.get('ebit_margin'))
        pts = 15 if ebit_m > 20 else (7.5 if ebit_m >= 10 else 0)
        add_h("EBIT Margin", ebit_m, pts, 15, False)

        roic = clean_percent(metrics.get('roic'))
        pts = 20 if roic > 15 else (10 if roic >= 8 else 0)
        add_h("ROIC", roic, pts, 20, False)

        fcf_trend = metrics.get('fcf_trend', 'Flat')
        pts = 15 if fcf_trend == "Growing" else 0
        add_h("FCF Trend", fcf_trend, pts, 15, "raw")

        # BUY (100 pct)
        pts = 30 if mos > 20 else (15 if mos >= 0 else 0)
        add_b("Margin of Safety", mos, pts, 30, False)

        pts = 20 if rev_g > 15 else (10 if rev_g >= 5 else 0)
        add_b("Revenue Growth (Next 3Y)", rev_g, pts, 20, False)

        # P/E Ratio (HYBRID BLENDED SCORE - 20 pct max)
        pe_5y = clean_ratio(metrics.get('pe_historic'))
        # Part A: Absolute (10 pct)
        pts_abs = 10 if (pe > 0 and pe < 15.0) else (5 if (pe > 0 and pe <= 25.0) else 0)
        # Part B: Relative to 5Y Avg (10 pct)
        pts_rel = 0
        if pe > 0 and pe_5y > 0:
            pe_diff_pct = ((pe - pe_5y) / pe_5y) * 100
            pts_rel = 10 if pe_diff_pct < -15 else (5 if abs(pe_diff_pct) <= 15 else 0)
        pts = pts_abs + pts_rel
        add_b("P/E Ratio", pe, pts, 20, True)

        ev_ebitda = clean_ratio(metrics.get('ev_to_ebitda'))
        pts = 10 if (ev_ebitda > 0 and ev_ebitda < 12.0) else (5 if (ev_ebitda > 0 and ev_ebitda <= 18.0) else 0)
        add_b("EV / EBITDA", ev_ebitda, pts, 10, True)

        ps = clean_ratio(metrics.get('ps_ratio'))
        pts = 10 if (ps > 0 and ps < 4.0) else (5 if (ps > 0 and ps <= 8.0) else 0)
        add_b("P/S Ratio", ps, pts, 10, True)

        f_peg = clean_ratio(metrics.get('peg_ratio'))
        pts = 10 if (f_peg > 0 and f_peg < 1.2) else (5 if (f_peg > 0 and f_peg <= 2.0) else 0)
        add_b("PEG Ratio", f_peg, pts, 10, True)

    return {
        "health_score_total": min(int(h_score), 100),
        "good_to_buy_total": min(int(b_score), 100),
        "health_breakdown": h_breakdown,
        "buy_breakdown": b_breakdown
    }

def calculate_health_score(metrics):
    res = calculate_scoring_reform({"margin_of_safety": 0}, metrics)
    return {"total": res["health_score_total"], "breakdown": res["health_breakdown"]}

def calculate_buy_score(valuation_data, metrics):
    res = calculate_scoring_reform(valuation_data, metrics)
    return {"total": res["good_to_buy_total"], "breakdown": res["buy_breakdown"]}


def calculate_piotroski_score(metrics):
    """
    Calculates the Piotroski F-Score (0-9) based on 9 binary criteria.
    Groups: Profitability (F1-F4), Leverage & Liquidity (F5-F7), Operating Efficiency (F8-F9).
    Uses historical_anchors for YoY delta calculations when available.
    Missing data => criterion is skipped (not penalized), marked as None.
    """

    def safe_float(val, default=None):
        if val is None:
            return default
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    breakdown = []
    total_score = 0
    total_possible = 0  # Track how many criteria had data

    # ── Extract current-year and prior-year from historical_anchors ────────────
    anchors = metrics.get("historical_anchors") or []
    # historical_anchors may contain estimated years — filter to reported only
    reported = [a for a in anchors if "(Est)" not in str(a.get("year", ""))]
    # Sort ascending by year number
    def yr_num(a):
        y = str(a.get("year", "0"))
        nums = "".join(filter(str.isdigit, y))
        return int(nums) if nums else 0
    reported.sort(key=yr_num)

    # Current = most recent reported, prior = one before that
    anchor_cur = reported[-1] if len(reported) >= 1 else {}
    anchor_pri = reported[-2] if len(reported) >= 2 else {}

    # ── Current-year scalars from live scraper data ────────────────────────────
    roa_cur       = safe_float(metrics.get("roa"))              # decimal e.g. 0.12 = 12%
    cfo_cur       = safe_float(metrics.get("operating_cash_flow") or metrics.get("fcf"))
    current_ratio = safe_float(metrics.get("current_ratio"))
    total_assets  = safe_float(metrics.get("total_assets"))
    total_debt    = safe_float(metrics.get("total_debt"))
    shares_cur    = safe_float(metrics.get("shares_outstanding"))
    gross_margin  = safe_float(metrics.get("gross_margin") or metrics.get("gross_margins"))
    revenue_cur   = safe_float(metrics.get("revenue"))

    # Normalise roa: if stored as percentage (e.g. 12.0) convert to decimal
    if roa_cur is not None and abs(roa_cur) > 1.5:
        roa_cur = roa_cur / 100.0

    # ── Prior-year scalars from historical_anchors ─────────────────────────────
    # anchors store revenue_b (billions), net_margin_pct (string "12.3%"), shares_out_b
    def pct_from_str(s):
        """Parse '12.3%' -> 0.123"""
        if s is None:
            return None
        try:
            return float(str(s).replace("%", "").strip()) / 100.0
        except:
            return None

    def net_income_from_anchor(a):
        rev_b = safe_float(a.get("revenue_b"))
        nm    = pct_from_str(a.get("net_margin_pct"))
        if rev_b is not None and nm is not None:
            return rev_b * 1e9 * nm
        return None

    # Derive prior ROA from anchor net income / (total_assets proxy via revenue scale)
    # We don't have prior total assets directly, so we approximate:
    # Prior ROA ≈ (prior net income) / (prior revenue * asset_turnover_proxy)
    # Simpler: compare net_margin as ROA proxy when assets unknown
    net_margin_cur = pct_from_str(anchor_cur.get("net_margin_pct")) if anchor_cur else None
    net_margin_pri = pct_from_str(anchor_pri.get("net_margin_pct")) if anchor_pri else None
    # Fall back to direct roa from metrics for current
    roa_approx_cur = roa_cur if roa_cur is not None else net_margin_cur
    roa_approx_pri = net_margin_pri  # best proxy we have for prior year

    # Prior long-term debt proxy: we use total_debt from anchor (debt_b field)
    debt_b_cur = safe_float(anchor_cur.get("total_debt_b")) if anchor_cur else None
    debt_b_pri = safe_float(anchor_pri.get("total_debt_b")) if anchor_pri else None
    debt_cur_raw = (debt_b_cur * 1e9) if debt_b_cur is not None else total_debt
    debt_pri_raw = (debt_b_pri * 1e9) if debt_b_pri is not None else None

    # Prior shares
    shares_b_cur = safe_float(anchor_cur.get("shares_out_b")) if anchor_cur else None
    shares_b_pri = safe_float(anchor_pri.get("shares_out_b")) if anchor_pri else None
    shares_prior = (shares_b_pri * 1e9) if shares_b_pri is not None else None

    # Asset turnover (revenue / assets) — proxy for F9
    # We approximate prior asset turnover via revenue_b change vs. shares proxy
    rev_b_cur = safe_float(anchor_cur.get("revenue_b")) if anchor_cur else None
    rev_b_pri = safe_float(anchor_pri.get("revenue_b")) if anchor_pri else None

    # ── Helper to add a criterion ──────────────────────────────────────────────
    def add_criterion(group, name, description, value_str, passed):
        nonlocal total_score, total_possible
        if passed is None:
            # Data not available — skip (no penalty)
            pt = None
        else:
            pt = 1 if passed else 0
            total_score += pt
            total_possible += 1
        breakdown.append({
            "group": group,
            "criterion": name,
            "description": description,
            "value": value_str,
            "passed": passed,
            "points_awarded": pt,
            "max_points": 1
        })

    # ════════════════════════════════════════════════════════════
    # GROUP 1: PROFITABILITY
    # ════════════════════════════════════════════════════════════

    # F1 — ROA > 0
    if roa_approx_cur is not None:
        add_criterion(
            "Profitability", "ROA > 0 (F1)",
            "Return on Assets is positive",
            f"{roa_approx_cur*100:.2f}%",
            roa_approx_cur > 0
        )
    else:
        add_criterion("Profitability", "ROA > 0 (F1)", "Return on Assets is positive", "N/A", None)

    # F2 — Operating Cash Flow > 0
    if cfo_cur is not None:
        add_criterion(
            "Profitability", "Operating CFO > 0 (F2)",
            "Operating cash flow is positive",
            f"${cfo_cur/1e9:.2f}B" if abs(cfo_cur) >= 1e8 else f"${cfo_cur:,.0f}",
            cfo_cur > 0
        )
    else:
        add_criterion("Profitability", "Operating CFO > 0 (F2)", "Operating cash flow is positive", "N/A", None)

    # F3 — Δ ROA (improving year-over-year)
    if roa_approx_cur is not None and roa_approx_pri is not None:
        add_criterion(
            "Profitability", "Δ ROA Improving (F3)",
            "ROA increased vs prior year",
            f"{roa_approx_cur*100:.2f}% vs {roa_approx_pri*100:.2f}% prior",
            roa_approx_cur > roa_approx_pri
        )
    else:
        add_criterion("Profitability", "Δ ROA Improving (F3)", "ROA increased vs prior year", "N/A", None)

    # F4 — Accruals: CFO / Assets > ROA (cash quality of earnings)
    if cfo_cur is not None and total_assets and total_assets > 0 and roa_approx_cur is not None:
        cfo_to_assets = cfo_cur / total_assets
        add_criterion(
            "Profitability", "Accruals (CFO Quality) (F4)",
            "CFO/Assets > ROA — profit backed by real cash",
            f"CFO/A={cfo_to_assets*100:.2f}% vs ROA={roa_approx_cur*100:.2f}%",
            cfo_to_assets > roa_approx_cur
        )
    else:
        add_criterion("Profitability", "Accruals (CFO Quality) (F4)", "CFO/Assets > ROA", "N/A", None)

    # ════════════════════════════════════════════════════════════
    # GROUP 2: LEVERAGE & LIQUIDITY
    # ════════════════════════════════════════════════════════════

    # F5 — Δ Leverage: Long-term debt decreased (or stayed same)
    if debt_cur_raw is not None and debt_pri_raw is not None:
        add_criterion(
            "Leverage & Liquidity", "Δ Leverage ↓ (F5)",
            "Long-term debt did not increase",
            f"${debt_cur_raw/1e9:.2f}B vs ${debt_pri_raw/1e9:.2f}B prior",
            debt_cur_raw <= debt_pri_raw
        )
    else:
        add_criterion("Leverage & Liquidity", "Δ Leverage ↓ (F5)", "Long-term debt did not increase", "N/A", None)

    # F6 — Δ Current Ratio: Improving liquidity
    # We only have current year current_ratio; compare vs gross margin trend as proxy
    # If we have 2 anchor years with implied liquidity proxy — use cash_b / debt_b proxy
    cash_b_cur = safe_float(anchor_cur.get("cash_b")) if anchor_cur else None
    cash_b_pri = safe_float(anchor_pri.get("cash_b")) if anchor_pri else None
    if current_ratio is not None and cash_b_cur is not None and cash_b_pri is not None and debt_b_cur and debt_b_pri:
        # Proxy: cash-to-debt ratio YoY
        liq_cur = cash_b_cur / debt_b_cur if debt_b_cur > 0 else None
        liq_pri = cash_b_pri / debt_b_pri if debt_b_pri > 0 else None
        if liq_cur is not None and liq_pri is not None:
            add_criterion(
                "Leverage & Liquidity", "Δ Current Ratio ↑ (F6)",
                "Liquidity (cash/debt) improved vs prior year",
                f"{liq_cur:.2f}x vs {liq_pri:.2f}x prior",
                liq_cur >= liq_pri
            )
        else:
            add_criterion("Leverage & Liquidity", "Δ Current Ratio ↑ (F6)", "Liquidity improved vs prior year", "N/A", None)
    elif current_ratio is not None:
        # We have current ratio but no prior year — just check > 1.0 as baseline
        add_criterion(
            "Leverage & Liquidity", "Current Ratio > 1.0 (F6)",
            "Current ratio above 1 (adequate liquidity)",
            f"{current_ratio:.2f}x",
            current_ratio >= 1.0
        )
    else:
        add_criterion("Leverage & Liquidity", "Δ Current Ratio ↑ (F6)", "Liquidity improved vs prior year", "N/A", None)

    # F7 — No dilution (shares did not increase)
    if shares_cur is not None and shares_prior is not None:
        add_criterion(
            "Leverage & Liquidity", "No Dilution (F7)",
            "Share count did not increase (no new equity issued)",
            f"{shares_cur/1e9:.3f}B vs {shares_prior/1e9:.3f}B prior",
            shares_cur <= shares_prior * 1.01  # 1% tolerance
        )
    elif shares_b_cur is not None and shares_b_pri is not None:
        add_criterion(
            "Leverage & Liquidity", "No Dilution (F7)",
            "Share count did not increase (no new equity issued)",
            f"{shares_b_cur:.3f}B vs {shares_b_pri:.3f}B prior",
            shares_b_cur <= shares_b_pri * 1.01
        )
    else:
        add_criterion("Leverage & Liquidity", "No Dilution (F7)", "No new equity issued", "N/A", None)

    # ════════════════════════════════════════════════════════════
    # GROUP 3: OPERATING EFFICIENCY
    # ════════════════════════════════════════════════════════════

    # F8 — Δ Gross Margin improving
    gm_raw = safe_float(metrics.get("gross_margin") or metrics.get("gross_margins"))
    if gm_raw is not None and abs(gm_raw) > 1.5:
        gm_raw = gm_raw / 100.0  # normalise from 62.0 -> 0.62
    # Prior gross margin from anchors: net_margin_pct is a proxy (not gross), use revenue vs net income
    # Better: use operating_margin for the delta trend
    op_margin_cur = safe_float(metrics.get("operating_margin"))
    if op_margin_cur is not None and abs(op_margin_cur) > 1.5:
        op_margin_cur = op_margin_cur / 100.0

    if net_margin_cur is not None and net_margin_pri is not None:
        add_criterion(
            "Operating Efficiency", "Δ Gross Margin ↑ (F8)",
            "Net margin improved vs prior year (proxy for gross margin trend)",
            f"{net_margin_cur*100:.2f}% vs {net_margin_pri*100:.2f}% prior",
            net_margin_cur > net_margin_pri
        )
    elif gm_raw is not None:
        add_criterion(
            "Operating Efficiency", "Gross Margin > 20% (F8)",
            "Gross margin above 20% (healthy profitability)",
            f"{gm_raw*100:.1f}%",
            gm_raw > 0.20
        )
    else:
        add_criterion("Operating Efficiency", "Δ Gross Margin ↑ (F8)", "Gross margin improved vs prior year", "N/A", None)

    # F9 — Δ Asset Turnover improving (revenue growth vs prior year as proxy)
    if rev_b_cur is not None and rev_b_pri is not None and rev_b_pri > 0:
        rev_growth = (rev_b_cur - rev_b_pri) / rev_b_pri
        add_criterion(
            "Operating Efficiency", "Δ Asset Turnover ↑ (F9)",
            "Revenue grew vs prior year (asset efficiency improving)",
            f"${rev_b_cur:.2f}B vs ${rev_b_pri:.2f}B ({rev_growth*100:+.1f}%)",
            rev_growth > 0
        )
    else:
        add_criterion("Operating Efficiency", "Δ Asset Turnover ↑ (F9)", "Asset turnover improved vs prior year", "N/A", None)

    # ── Final score ────────────────────────────────────────────────────────────
    # Interpretation
    if total_possible == 0:
        label = "N/A"
    elif total_score >= 7:
        label = "Strong"
    elif total_score >= 4:
        label = "Neutral"
    else:
        label = "Weak"

    return {
        "score": total_score,
        "max_possible": total_possible,
        "label": label,
        "breakdown": breakdown
    }

