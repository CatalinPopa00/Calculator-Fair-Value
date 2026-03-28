def clean_percent(val):
    """
    CLEANING RULE: If a percentage metric (ROIC, Margins, Growth, MOS) 
    comes as a decimal (e.g. 0.3), multiply by 100 to work with integers (30%).
    """
    if val is None: return None
    try:
        f_val = float(val)
        if abs(f_val) < 1.0 and f_val != 0:
            return f_val * 100.0
        return f_val
    except:
        return None

def calculate_scoring_reform(valuation_data: dict, metrics: dict):
    """
    Expert Quantitative Evaluation System.
    STRICT READ AND CALCULATE ONLY. NO OVERWRITING RAW DATABASE VALUES.
    """
    sector = metrics.get('sector', '')
    
    # 1. Health Score Calculation
    h_score = 0
    h_breakdown = []
    
    def add_h(metric_name, value, pts, max_pts):
        nonlocal h_score
        h_score += pts
        h_breakdown.append({
            "metric": metric_name,
            "value": f"{value:.2f}x" if any(x in metric_name for x in ["Ratio", "Coverage", "Debt-to", "Price-to"]) else (f"{value:.1f}%" if value is not None and isinstance(value, (int, float)) else str(value)),
            "points_awarded": int(pts),
            "max_points": int(max_pts)
        })

    # --- Metrics for Health ---
    de = metrics.get('debt_to_equity')
    ic = metrics.get('interest_coverage')
    cr = metrics.get('current_ratio')
    ebit_m = clean_percent(metrics.get('ebit_margin') or metrics.get('operating_margin'))
    roic = clean_percent(metrics.get('roic') or metrics.get('roa') or metrics.get('roe'))
    fcf_hist = metrics.get('fcf_history', [])
    fcf_cagr = clean_percent(metrics.get('historic_fcf_growth'))

    # [1] DEBT-TO-EQUITY (Always default)
    pts = 0
    if de is not None:
        if de < 0.8: pts = 20
        elif de <= 1.5: pts = 10
    add_h("Debt-to-Equity", de, pts, 20)

    # [2] INTEREST COVERAGE / NIM / D-TO-EBITDA
    if sector == "Financial Services":
        nim = metrics.get('nim') or (metrics.get('operating_margin') if metrics.get('operating_margin') else 2.5)
        pts = 0
        if nim > 3.0: pts = 15
        elif nim >= 1.5: pts = 7.5
        add_h("Net Interest Margin (NIM)", nim, pts, 15)
    else:
        # Default for non-financials
        pts = 0
        if ic is not None:
            if ic > 10: pts = 15
            elif ic >= 3: pts = 7.5
        add_h("Interest Coverage", ic, pts, 15)

    # [3] CURRENT RATIO / CET1 / DEBT-TO-EBITDA
    if sector == "Financial Services":
        cet1 = metrics.get('cet1_ratio') or metrics.get('common_equity_tier_1') or 13.0
        pts = 0
        if cet1 > 12: pts = 15
        elif cet1 >= 9: pts = 7.5
        add_h("CET1 Ratio", cet1, pts, 15)
    elif sector == "Real Estate":
        td = metrics.get('total_debt')
        ebitda = metrics.get('ebitda')
        dte = (td/ebitda) if td and ebitda and ebitda > 0 else (metrics.get('debt_to_ebitda') or 5.0)
        pts = 0
        if dte < 5.5: pts = 15
        elif dte <= 7.0: pts = 7.5
        add_h("Debt-to-EBITDA", dte, pts, 15)
    else:
        pts = 0
        if cr is not None:
            if cr > 1.2: pts = 15
            elif cr >= 0.8: pts = 7.5
        add_h("Current Ratio", cr, pts, 15)

    # [4] EBIT MARGIN / ROE / AFFO MARGIN
    if sector == "Financial Services":
        roe = clean_percent(metrics.get('roe') or 12.0)
        pts = 0
        if roe > 15: pts = 15
        elif roe >= 8: pts = 7.5
        add_h("ROE", roe, pts, 15)
    elif sector == "Real Estate":
        affo_m = clean_percent(metrics.get('affo_margin') or (ebit_m * 0.9 if ebit_m else 45.0))
        pts = 0
        if affo_m > 50: pts = 15
        elif affo_m >= 30: pts = 7.5
        add_h("AFFO Margin", affo_m, pts, 15)
    else:
        pts = 0
        if ebit_m is not None:
            if ebit_m > 20: pts = 15
            elif ebit_m >= 10: pts = 7.5
        add_h("EBIT Margin", ebit_m, pts, 15)

    # [5] ROIC / ROA
    if sector == "Financial Services":
        roa = clean_percent(metrics.get('roa') or 1.2)
        pts = 0
        if roa > 1.5: pts = 20
        elif roa >= 0.5: pts = 10
        add_h("ROA", roa, pts, 20)
    else:
        pts = 0
        if roic is not None:
            if roic > 15: pts = 20
            elif roic >= 8: pts = 10
        add_h("ROIC", roic, pts, 20)

    # [6] FCF TREND / BVPS GROWTH / AFFO GROWTH
    if sector == "Financial Services":
        bv_growth = clean_percent(metrics.get('historic_bvps_growth') or metrics.get('eps_growth') or 5.0)
        pts = 0
        if bv_growth > 8: pts = 15
        elif bv_growth >= 3: pts = 7.5
        add_h("BVPS Growth", bv_growth, pts, 15)
    elif sector == "Real Estate":
        affo_g = clean_percent(metrics.get('affo_growth') or fcf_cagr or 3.0)
        pts = 0
        if affo_g > 5: pts = 15
        elif affo_g >= 2: pts = 7.5
        add_h("AFFO Growth", affo_g, pts, 15)
    else:
        pts = 0
        is_increasing = False
        if fcf_hist and len(fcf_hist) >= 2:
            if fcf_hist[0] > fcf_hist[-1]: is_increasing = True # newest first
        if is_increasing or (fcf_cagr and fcf_cagr > 5):
            pts = 15
        add_h("FCF Trend", "Crescător" if pts > 0 else "Stabil/Scădere", pts, 15)

    # 2. Buy Score Calculation
    b_score = 0
    b_breakdown = []
    
    def add_b(metric_name, value, pts, max_pts):
        nonlocal b_score
        b_score += pts
        b_breakdown.append({
            "metric": metric_name,
            "value": f"{value:.2f}x" if any(x in metric_name for x in ["Ratio", "P/E", "P/S", "Price-to", "Index"]) else (f"{value:.1f}%" if value is not None and isinstance(value, (int, float)) else str(value)),
            "points_awarded": int(pts),
            "max_points": int(max_pts)
        })

    # [1] MARGIN OF SAFETY (Always default)
    mos = clean_percent(valuation_data.get('margin_of_safety'))
    pts = 0
    if mos is not None:
        if mos > 20: pts = 30
        elif mos >= 0: pts = 15
    add_b("Margin of Safety", mos, pts, 30)

    # [2] PEG RATIO (Always default)
    peg = metrics.get('peg_ratio')
    pts = 0
    if peg is not None:
        if peg < 1.0: pts = 15
        elif peg <= 1.5: pts = 7.5
    add_b("PEG Ratio", peg, pts, 15)

    # [3] FWD P/E / PRICE-TO-AFFO
    fpe = metrics.get('forward_pe') or metrics.get('pe_ratio')
    if sector == "Real Estate":
        p_affo = metrics.get('price_to_affo') or (metrics.get('pe_ratio') * 0.8 if metrics.get('pe_ratio') else 12.0)
        pts = 0
        if p_affo < 15: pts = 15
        elif p_affo <= 20: pts = 7.5
        add_b("Price-to-AFFO", p_affo, pts, 15)
    else:
        pts = 0
        if fpe is not None:
            if fpe < 15: pts = 15
            elif fpe <= 25: pts = 7.5
        add_b("Fwd P/E", fpe, pts, 15)

    # [4] FWD P/S / PRICE-TO-BOOK / DIV YIELD
    fps = metrics.get('fwd_ps') or metrics.get('ps_ratio')
    div_y = clean_percent(metrics.get('dividend_yield'))
    if sector == "Financial Services":
        ptb = metrics.get('price_to_book') or 1.1
        pts = 0
        if ptb < 1.2: pts = 15
        elif ptb <= 2.0: pts = 7.5
        add_b("Price-to-Book", ptb, pts, 15)
    elif sector == "Real Estate":
        pts = 0
        if div_y is not None:
            if div_y > 5: pts = 15
            elif div_y >= 3: pts = 7.5
        add_b("Dividend Yield", div_y, pts, 15)
    else:
        pts = 0
        if fps is not None:
            if fps < 3.0: pts = 15
            elif fps <= 8.0: pts = 7.5
        add_b("Fwd P/S", fps, pts, 15)

    # [5] FCF YIELD / DIV YIELD
    fcf_y = clean_percent((metrics.get('fcf') / metrics.get('market_cap')) * 100 if metrics.get('fcf') and metrics.get('market_cap') else None)
    if sector == "Financial Services":
        pts = 0
        if div_y is not None:
            if div_y > 4: pts = 15
            elif div_y >= 2: pts = 7.5
        add_b("Dividend Yield", div_y, pts, 15)
    else:
        pts = 0
        if fcf_y is not None:
            if fcf_y > 7: pts = 15
            elif fcf_y >= 3: pts = 7.5
        add_b("FCF Yield", fcf_y, pts, 15)

    # [6] NEXT 3Y REV GROWTH
    rev_g = clean_percent(metrics.get('next_3y_rev_est') or metrics.get('revenue_growth'))
    pts = 0
    if rev_g is not None:
        if rev_g > 10: pts = 10
        elif rev_g >= 5: pts = 5
    add_h_or_b = add_b # Next 3Y is in Buy breakdown
    add_h_or_b("Next 3Y Rev Growth", rev_g, pts, 10)

    return {
        "health_score_total": int(h_score),
        "good_to_buy_total": int(b_score),
        "health_breakdown": h_breakdown,
        "buy_breakdown": b_breakdown
    }

def calculate_health_score(metrics: dict):
    res = calculate_scoring_reform({"margin_of_safety": metrics.get('margin_of_safety')}, metrics)
    return {"total": res["health_score_total"], "breakdown": res["health_breakdown"]}

def calculate_buy_score(valuation_data: dict, metrics: dict):
    res = calculate_scoring_reform(valuation_data, metrics)
    return {"total": res["good_to_buy_total"], "breakdown": res["buy_breakdown"]}
