def clean_percent(val):
    if val is None: return None
    try:
        f_val = float(val)
        if 0 < abs(f_val) < 1.0:
            return f_val * 100.0
        return f_val
    except:
        return None

def calculate_scoring_reform(valuation_data, metrics):
    sector = metrics.get('sector', 'Technology')
    h_score = 0
    h_breakdown = []
    b_score = 0
    b_breakdown = []

    def format_val(value, is_ratio=True):
        if value is None: return "N/A"
        if is_ratio is True: return f"{value:.2f}x"
        if is_ratio is False: return f"{value:.1f}%"
        return str(value)

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

    mos = clean_percent(valuation_data.get('margin_of_safety'))
    rev_g = clean_percent(metrics.get('next_3y_rev_est') or metrics.get('revenue_growth'))
    peg = metrics.get('peg_ratio') or 1.5
    div_y = clean_percent(metrics.get('dividend_yield'))
    roic = clean_percent(metrics.get('roic') or metrics.get('roa') or 10.0)

    if sector == "Financial Services":
        # HEALTH (100 pts)
        de = metrics.get('debt_to_equity')
        pts = 20 if (de is not None and de < 0.8) else (10 if (de is not None and de <= 1.5) else 0)
        add_h("Debt-to-Equity", de, pts, 20, True)

        nim = clean_percent(metrics.get('nim') or 2.5)
        pts = 15 if (nim is not None and nim > 3.0) else (7.5 if (nim is not None and nim >= 1.5) else 0)
        add_h("Net Interest Margin", nim, pts, 15, False)

        cet1 = metrics.get('cet1_ratio') or metrics.get('common_equity_tier_1') or 11.0
        pts = 15 if (cet1 is not None and cet1 > 12) else (7.5 if (cet1 is not None and cet1 >= 9) else 0)
        add_h("CET1 Ratio", cet1, pts, 15, False)

        roe = clean_percent(metrics.get('roe') or 10.0)
        pts = 15 if (roe is not None and roe > 15) else (7.5 if (roe is not None and roe >= 8) else 0)
        add_h("ROE", roe, pts, 15, False)

        roa = clean_percent(metrics.get('roa') or 1.0)
        pts = 20 if (roa is not None and roa > 1.5) else (10 if (roa is not None and roa >= 0.5) else 0)
        add_h("ROA", roa, pts, 20, False)

        bvps = clean_percent(metrics.get('bvps_growth') or metrics.get('historic_bvps_growth') or 5.0)
        pts = 15 if (bvps is not None and bvps > 8) else (7.5 if (bvps is not None and bvps >= 3) else 0)
        add_h("BVPS Growth", bvps, pts, 15, False)

        # BUY (100 pts)
        pts = 15 if (peg is not None and peg < 1.0) else (7.5 if (peg is not None and peg <= 1.5) else 0)
        add_b("PEG Ratio", peg, pts, 15, True)

        pe = metrics.get('forward_pe') or metrics.get('pe_ratio') or 12.0
        pts = 15 if (pe is not None and pe < 10) else (7.5 if (pe is not None and pe <= 15) else 0)
        add_b("P/E Ratio", pe, pts, 15, True)

        ptb = metrics.get('price_to_book') or 1.5
        pts = 15 if (ptb is not None and ptb < 1.2) else (7.5 if (ptb is not None and ptb <= 2.0) else 0)
        add_b("Price-to-Book", ptb, pts, 15, True)

        pts = 15 if (div_y is not None and div_y > 4) else (7.5 if (div_y is not None and div_y >= 2) else 0)
        add_b("Dividend Yield", div_y, pts, 15, False)

        pts = 30 if (mos is not None and mos > 20) else (15 if (mos is not None and mos >= 0) else 0)
        add_b("Margin of Safety", mos, pts, 30, False)

        pts = 10 if (rev_g is not None and rev_g > 10) else (5 if (rev_g is not None and rev_g >= 5) else 0)
        add_b("Revenue Growth", rev_g, pts, 10, False)

    elif sector == "Real Estate":
        # HEALTH (100 pts)
        nd_ebitda = metrics.get('debt_to_ebitda') or 6.5
        pts = 20 if (nd_ebitda is not None and nd_ebitda < 6) else (10 if (nd_ebitda is not None and nd_ebitda <= 8) else 0)
        add_h("Net Debt / EBITDA", nd_ebitda, pts, 20, True)

        ic = metrics.get('interest_coverage') or 2.5
        pts = 10 if (ic is not None and ic > 4) else (5 if (ic is not None and ic >= 2) else 0)
        add_h("Interest Coverage", ic, pts, 10, True)

        cr = metrics.get('current_ratio')
        pts = 15 if (cr is not None and cr > 1.2) else (7.5 if (cr is not None and cr >= 0.8) else 0)
        add_h("Current Ratio", cr, pts, 15, True)

        affo_p = clean_percent(metrics.get('affo_payout') or 85.0)
        pts = 15 if (affo_p is not None and affo_p < 80) else (7.5 if (affo_p is not None and affo_p <= 95) else 0)
        add_h("AFFO Payout Ratio", affo_p, pts, 15, False)

        occ = clean_percent(metrics.get('occupancy_rate') or 94.0)
        pts = 20 if (occ is not None and occ > 95) else (10 if (occ is not None and occ >= 90) else 0)
        add_h("Occupancy Rate", occ, pts, 20, False)

        fcc = metrics.get('fixed_charge_coverage') or 2.5
        pts = 20 if (fcc is not None and fcc > 3) else (10 if (fcc is not None and fcc >= 1.5) else 0)
        add_h("Fixed Charge Coverage", fcc, pts, 20, True)

        # BUY (100 pts)
        p_affo = metrics.get('price_to_affo') or metrics.get('forward_pe') or 16.0
        pts = 20 if (p_affo is not None and p_affo < 15) else (10 if (p_affo is not None and p_affo <= 20) else 0)
        add_b("Price / AFFO", p_affo, pts, 20, True)

        p_nav = metrics.get('price_to_nav') or 1.1
        pts = 10 if (p_nav is not None and p_nav < 1.0) else (5 if (p_nav is not None and p_nav <= 1.2) else 0)
        add_b("Price / NAV", p_nav, pts, 10, True)

        pts = 10 if (div_y is not None and div_y > 5) else (5 if (div_y is not None and div_y >= 3) else 0)
        add_b("Dividend Yield", div_y, pts, 10, False)

        pts = 20 if (rev_g is not None and rev_g > 8) else (10 if (rev_g is not None and rev_g >= 4) else 0)
        add_b("Revenue Growth", rev_g, pts, 20, False)

        pts = 30 if (mos is not None and mos > 20) else (15 if (mos is not None and mos >= 0) else 0)
        add_b("Margin of Safety", mos, pts, 30, False)

        pts = 10 if (peg is not None and peg < 1.0) else (5 if (peg is not None and peg <= 2.0) else 0)
        add_b("PEG Ratio", peg, pts, 10, True)

    else:
        # DEFAULT TEMPLATE (Technology, Consumer, etc.)
        # HEALTH (100 pts)
        de = metrics.get('debt_to_equity')
        pts = 20 if (de is not None and de < 0.8) else (10 if (de is not None and de <= 1.5) else 0)
        add_h("Debt-to-Equity", de, pts, 20, True)

        ic = metrics.get('interest_coverage')
        pts = 15 if (ic is not None and ic > 10) else (7.5 if (ic is not None and ic >= 3) else 0)
        add_h("Interest Coverage", ic, pts, 15, True)

        cr = metrics.get('current_ratio')
        pts = 15 if (cr is not None and cr > 1.2) else (7.5 if (cr is not None and cr >= 0.8) else 0)
        add_h("Current Ratio", cr, pts, 15, True)

        ebit_m = clean_percent(metrics.get('ebit_margin') or metrics.get('operating_margin') or 15.0)
        pts = 15 if (ebit_m is not None and ebit_m > 20) else (7.5 if (ebit_m is not None and ebit_m >= 10) else 0)
        add_h("EBIT Margin", ebit_m, pts, 15, False)

        pts = 20 if (roic is not None and roic > 15) else (10 if (roic is not None and roic >= 8) else 0)
        add_h("ROIC", roic, pts, 20, False)

        fcf_m = clean_percent(metrics.get('fcf_margin') or 12.0)
        pts = 15 if (fcf_m is not None and fcf_m > 15) else (7.5 if (fcf_m is not None and fcf_m >= 8) else 0)
        add_h("FCF Margin", fcf_m, pts, 15, False)

        # BUY (100 pts)
        pe = metrics.get('forward_pe') or metrics.get('pe_ratio') or 20.0
        pts = 20 if (pe is not None and pe < 15) else (10 if (pe is not None and pe <= 25) else 0)
        add_b("P/E Ratio", pe, pts, 20, True)

        ev_ebitda = metrics.get('ev_to_ebitda') or 14.0
        pts = 10 if (ev_ebitda is not None and ev_ebitda < 12) else (5 if (ev_ebitda is not None and ev_ebitda <= 18) else 0)
        add_b("EV / EBITDA", ev_ebitda, pts, 10, True)

        ps = metrics.get('ps_ratio') or 4.0
        pts = 10 if (ps is not None and ps < 3.0) else (5 if (ps is not None and ps <= 8.0) else 0)
        add_b("P/S Ratio", ps, pts, 10, True)

        pts = 20 if (rev_g is not None and rev_g > 10) else (10 if (rev_g is not None and rev_g >= 5) else 0)
        add_b("Revenue Growth", rev_g, pts, 20, False)

        pts = 30 if (mos is not None and mos > 20) else (15 if (mos is not None and mos >= 0) else 0)
        add_b("Margin of Safety", mos, pts, 30, False)

        pts = 10 if (peg is not None and peg < 1.0) else (5 if (peg is not None and peg <= 1.5) else 0)
        add_b("PEG Ratio", peg, pts, 10, True)

    return {
        "health_score_total": int(h_score),
        "good_to_buy_total": int(b_score),
        "health_breakdown": h_breakdown,
        "buy_breakdown": b_breakdown
    }

def calculate_health_score(metrics):
    res = calculate_scoring_reform({"margin_of_safety": metrics.get('margin_of_safety')}, metrics)
    return {"total": res["health_score_total"], "breakdown": res["health_breakdown"]}

def calculate_buy_score(valuation_data, metrics):
    res = calculate_scoring_reform(valuation_data, metrics)
    return {"total": res["good_to_buy_total"], "breakdown": res["buy_breakdown"]}
