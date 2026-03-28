def clean_percent(val):
    if val is None: return 0.0
    try:
        f_val = float(val)
        # Standardize decimal (0.05 -> 5%) before calculation and display.
        if 0 < abs(f_val) < 1.0:
            return f_val * 100.0
        return f_val
    except:
        return 0.0

def calculate_scoring_reform(valuation_data, metrics):
    sector = metrics.get('sector', 'Technology')
    h_score = 0
    h_breakdown = []
    b_score = 0
    b_breakdown = []

    def format_val(value, is_ratio=True):
        if value is None: return "0.00"
        if is_ratio: return f"{value:.2f}x"
        return f"{value:.1f}%"

    def add_h(metric, value, pts, max_pts, is_ratio=True):
        nonlocal h_score
        h_score += pts
        h_breakdown.append({
            "metric": metric,
            "value": format_val(value, is_ratio),
            "points_awarded": int(pts),
            "max_points": int(max_pts)
        })

    def add_b(metric, value, pts, max_pts, is_ratio=True):
        nonlocal b_score
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
    peg = clean_percent(metrics.get('peg_ratio')) # Normalized to be safe
    # But PEG is a ratio, if it's 1.2 we keep it as 1.2.
    # PEG 0.05 -> 5.0x seems weird, however PEG usually > 0.1 for most companies.
    # Let's ensure ratios like PEG are not incorrectly multiplied.
    # Actually, clean_percent multiplies by 100 if abs < 1.0.
    # For PEG, if PEG = 0.8, it becomes 80.0. User said: 0.05 -> 5.
    # PEG is a ratio, it's NOT a percentage. Let's make separate clean_ratio.
    
    def clean_ratio(val):
        if val is None: return 0.0
        try: return float(val)
        except: return 0.0

    # USER-DRIVEN DATA MAPPING: TRAILING PE ONLY (FORBIDDEN FORWARD PE)
    pe = clean_ratio(metrics.get('trailing_pe') or metrics.get('pe_ratio'))

    if sector == "Financial Services":
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

        pts = 15 if (pe > 0 and pe < 10) else (7.5 if (pe > 0 and pe <= 15) else 0)
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

    elif sector == "Real Estate":
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

        f_peg = clean_ratio(metrics.get('peg_ratio'))
        pts = 15 if (f_peg > 0 and f_peg < 1.5) else (7.5 if (f_peg > 0 and f_peg <= 2.5) else 0)
        add_b("PEG Ratio", f_peg, pts, 15, True)

        p_affo = clean_ratio(metrics.get('price_to_affo'))
        pts = 15 if (p_affo > 0 and p_affo < 15) else (7.5 if (p_affo > 0 and p_affo <= 20) else 0)
        add_b("Price-to-AFFO", p_affo, pts, 15, True)

        div_y = clean_percent(metrics.get('dividend_yield'))
        pts = 15 if div_y > 5 else (7.5 if div_y >= 3 else 0)
        add_b("Dividend Yield", div_y, pts, 15, False)

        fcf_y = clean_percent(metrics.get('fcf_yield'))
        pts = 15 if fcf_y > 7 else (7.5 if fcf_y >= 3 else 0)
        add_b("FCF Yield", fcf_y, pts, 15, False)

        rev_g_3y = clean_percent(metrics.get('next_3y_rev_growth'))
        pts = 10 if rev_g_3y > 5 else (5 if rev_g_3y >= 2 else 0)
        add_b("Next 3Y Rev Growth", rev_g_3y, pts, 10, False)

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

        fcf_trend = metrics.get('fcf_trend', 'Altfel')
        pts = 15 if fcf_trend == "Crescător" else 0
        add_h("FCF Trend", fcf_trend, pts, 15, "raw")

        # BUY (100 pct)
        pts = 30 if mos > 20 else (15 if mos >= 0 else 0)
        add_b("Margin of Safety", mos, pts, 30, False)

        pts = 20 if rev_g > 15 else (10 if rev_g >= 5 else 0)
        add_b("Revenue Growth", rev_g, pts, 20, False)

        pts = 20 if (pe > 0 and pe < 15.0) else (10 if (pe > 0 and pe <= 25.0) else 0)
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
        "health_score_total": int(h_score),
        "good_to_buy_total": int(b_score),
        "health_breakdown": h_breakdown,
        "buy_breakdown": b_breakdown
    }

def calculate_health_score(metrics):
    res = calculate_scoring_reform({"margin_of_safety": 0}, metrics)
    return {"total": res["health_score_total"], "breakdown": res["health_breakdown"]}

def calculate_buy_score(valuation_data, metrics):
    res = calculate_scoring_reform(valuation_data, metrics)
    return {"total": res["good_to_buy_total"], "breakdown": res["buy_breakdown"]}
