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

    # SECTOR-SPECIFIC P/E MAPPING
    sector_lower = sector.lower()
    industry_lower = industry.lower()
    is_communication_tech = sector_lower == "communication services" and "telecom" not in industry_lower
    is_tech_software = sector_lower in ["technology"] or "software" in industry_lower or "internet" in industry_lower or is_communication_tech
    is_health_biotech = sector_lower in ["healthcare"] or "biotechnology" in industry_lower
    
    use_non_gaap = is_tech_software or is_health_biotech
    
    pe_label = "P/E Ratio"
    pe = 0
    if use_non_gaap:
        adj_eps = metrics.get('adjusted_eps')
        current_price = metrics.get('current_price') or valuation_data.get('current_price', 0)
        if adj_eps and current_price and clean_ratio(adj_eps) > 0:
            pe = clean_ratio(current_price / clean_ratio(adj_eps))
            pe_label = "P/E Ratio (adj.)"
        else:
            # fallback
            pe = valuation_data.get('pe')
            if not pe:
                pe = clean_ratio(metrics.get('trailing_pe') or metrics.get('pe_ratio'))
            else:
                pe = clean_ratio(pe)
            pe_label = "P/E Ratio (adj.)"
    else:
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
        if pe > 0 and pe_5y and pe_5y > 0.001:
            pe_diff_pct = ((pe - pe_5y) / pe_5y) * 100
            pts_rel = 7.5 if pe_diff_pct < -15 else (3.75 if abs(pe_diff_pct) <= 15 else 0)
        pts = pts_abs + pts_rel
        add_b(pe_label, pe, pts, 15, True)

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
        if pe > 0 and pe_5y and pe_5y > 0.001:
            pe_diff_pct = ((pe - pe_5y) / pe_5y) * 100
            pts_rel = 10 if pe_diff_pct < -15 else (5 if abs(pe_diff_pct) <= 15 else 0)
        pts = pts_abs + pts_rel
        add_b(pe_label, pe, pts, 20, True)

        ev_ebitda = clean_ratio(metrics.get('ev_to_ebitda'))
        pts = 10 if (ev_ebitda > 0 and ev_ebitda < 12.0) else (5 if (ev_ebitda > 0 and ev_ebitda <= 18.0) else 0)
        add_b("EV / EBITDA", ev_ebitda, pts, 10, True)

        ps = clean_ratio(metrics.get('ps_ratio') or metrics.get('price_to_sales'))
        pts = 10 if (ps > 0 and ps < 2.0) else (5 if (ps > 0 and ps <= 4.0) else 0)
        add_b("P/S Ratio", ps, pts, 10, True)

        f_peg = clean_ratio(metrics.get('peg_ratio'))
        pts = 10 if (f_peg > 0 and f_peg < 1.0) else (5 if (f_peg > 0 and f_peg <= 1.5) else 0)
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
    Calculates the Piotroski F-Score (0-9) based on STRICT binary criteria.
    Profitability: F1-F4
    Leverage & Liquidity: F5-F7
    Operating Efficiency: F8-F9
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
    total_possible = 9  # We always show 9 criteria

    # ── Extract current-year and prior-year from historical_anchors ────────────
    anchors = metrics.get("historical_anchors") or []
    reported = [a for a in anchors if "(Est)" not in str(a.get("year", ""))]
    
    def yr_num(a):
        y = str(a.get("year", "0"))
        nums = "".join(filter(str.isdigit, y))
        return int(nums) if nums else 0
    reported.sort(key=yr_num)

    anchor_cur = reported[-1] if len(reported) >= 1 else {}
    anchor_pri = reported[-2] if len(reported) >= 2 else {}

    # ── Current and Prior Scalars ──────────────────────────────────────────────
    def pct_from_str(s):
        if s is None: return None
        try: return float(str(s).replace("%", "").strip()) / 100.0
        except: return None

    # F1 Metrics
    net_income_cur = safe_float(metrics.get("net_income"))
    roa_cur = safe_float(metrics.get("roa"))
    if roa_cur is not None and abs(roa_cur) > 1.5: roa_cur /= 100.0

    # F2 Metrics
    cfo_cur = safe_float(metrics.get("operating_cashflow"))
    fcf_cur = safe_float(metrics.get("fcf"))
    
    # F3 Metrics
    # Use Net Margin from anchors as ROA proxy if ROA missing for delta
    nm_cur = pct_from_str(anchor_cur.get("net_margin_pct"))
    nm_pri = pct_from_str(anchor_pri.get("net_margin_pct"))
    roa_pri = safe_float(anchor_pri.get("roa")) or nm_pri # Fallback to Net Margin proxy
    roa_cur_final = roa_cur if roa_cur is not None else nm_cur
    
    # F4 Metrics (Accruals)
    # Net Profit fallback: Revenue * Net Margin
    rev_cur = safe_float(metrics.get("revenue"))
    net_profit_calc = net_income_cur if net_income_cur is not None else (rev_cur * nm_cur if rev_cur and nm_cur else None)
    cash_flow_for_f4 = cfo_cur if cfo_cur is not None else fcf_cur

    # F5 Metrics (Leverage)
    # v281: Prioritize anchor-to-anchor comparison for UI consistency. 
    # Added 1% tolerance for minor debt fluctuations.
    debt_b_cur = safe_float(anchor_cur.get("total_debt_b"))
    debt_b_pri = safe_float(anchor_pri.get("total_debt_b"))
    
    total_debt_cur = (debt_b_cur * 1e9) if debt_b_cur is not None else safe_float(metrics.get("total_debt"))
    total_debt_pri = (debt_b_pri * 1e9) if debt_b_pri is not None else None
    
    # F6 Metrics (Liquidity)
    cr_cur = safe_float(anchor_cur.get("current_ratio")) or safe_float(metrics.get("current_ratio"))
    cr_pri = safe_float(anchor_pri.get("current_ratio"))

    # F7 Metrics (No Dilution)
    shares_cur = safe_float(metrics.get("shares_outstanding"))
    shares_b_pri = safe_float(anchor_pri.get("shares_out_b"))
    shares_pri = (shares_b_pri * 1e9) if shares_b_pri is not None else None

    # F8 Metrics (Margin Delta)
    # Use net_margin or gross_margin trend
    gm_cur = safe_float(metrics.get("gross_margin") or metrics.get("gross_margins"))
    if gm_cur and abs(gm_cur) > 1.5: gm_cur /= 100.0
    gm_pri = pct_from_str(anchor_pri.get("gross_margin_pct")) # if available
    
    margin_cur = nm_cur if nm_cur is not None else gm_cur
    margin_pri = nm_pri if nm_pri is not None else gm_pri

    # F9 Metrics (ROIC / Efficiency)
    # Fallback to ROA if ROIC missing
    roic_cur = safe_float(metrics.get("roic")) or pct_from_str(anchor_cur.get("roic_pct"))
    if roic_cur and abs(roic_cur) > 1.5: roic_cur /= 100.0
    
    roic_pri = pct_from_str(anchor_pri.get("roic_pct"))
    if roic_pri and abs(roic_pri) > 1.5: roic_pri /= 100.0
    
    # Final Fallback: if data is still missing for ROIC delta, use ROA delta as proxy
    roic_cur_final = roic_cur if roic_cur is not None else roa_cur_final
    roic_pri_final = roic_pri if roic_pri is not None else roa_pri


    # ── Comparison Helper ──────────────────────────────────────────────────────
    def add_point(group, code, name, desc, val_str, passed):
        nonlocal total_score
        pt = 1 if (passed is True) else 0
        total_score += pt
        breakdown.append({
            "group": group,
            "criterion": f"{name} ({code})",
            "description": desc,
            "value": val_str if passed is not None else "Data Unavailable",
            "passed": passed if passed is not None else False,
            "points_awarded": pt,
            "max_points": 1
        })

    # ════════════════════════════════════════════════════════════
    # PROFITABILITY
    # ════════════════════════════════════════════════════════════
    
    # F1: ROA/Net Income > 0
    f1_val = roa_cur_final if roa_cur_final is not None else (net_income_cur/1e9 if net_income_cur else None)
    f1_passed = (roa_cur_final > 0) if roa_cur_final is not None else (net_income_cur > 0 if net_income_cur is not None else None)
    add_point("Profitability", "F1", "ROA / Net Profit", 
              "Company has positive Net Income or ROA",
              f"{roa_cur_final*100:.2f}%" if roa_cur_final is not None else ("Positive" if f1_passed else "Negative"),
              f1_passed)

    # F2: Cash Flow > 0
    f2_passed = (cash_flow_for_f4 > 0) if cash_flow_for_f4 is not None else None
    add_point("Profitability", "F2", "Cash Flow Positive", 
              "Operating Cash Flow (CFO) is positive",
              f"${cash_flow_for_f4/1e9:.2f}B" if (f2_passed is not None and cash_flow_for_f4) else "N/A",
              f2_passed)

    # F3: Delta ROA
    f3_passed = (roa_cur_final > roa_pri) if (roa_cur_final is not None and roa_pri is not None) else None
    add_point("Profitability", "F3", "Delta ROA", 
              "ROA is higher than in the previous year",
              f"{roa_cur_final*100:.1f}% vs {roa_pri*100:.1f}%" if f3_passed is not None else "N/A",
              f3_passed)

    # F4: Accruals
    f4_passed = (cash_flow_for_f4 > net_profit_calc) if (cash_flow_for_f4 is not None and net_profit_calc is not None) else None
    add_point("Profitability", "F4", "Accruals (Earnings Quality)", 
              "Cash Flow (CFO) is greater than Net Profit",
              f"CFO > Net Inc" if f4_passed is True else "CFO < Net Inc",
              f4_passed)

    # ════════════════════════════════════════════════════════════
    # LEVERAGE & LIQUIDITY
    # ════════════════════════════════════════════════════════════

    # F5: Delta Leverage (v281: Added 1% tolerance)
    f5_passed = (total_debt_cur <= (total_debt_pri * 1.01)) if (total_debt_cur is not None and total_debt_pri is not None) else None
    add_point("Leverage & Liquidity", "F5", "Delta Leverage", 
              "Total Debt decreased or stayed the same (1% margin)",
              f"${total_debt_cur/1e9:.2f}B vs ${total_debt_pri/1e9:.2f}B" if f5_passed is not None else "N/A",
              f5_passed)

    # F6: Delta Liquidity
    f6_passed = (cr_cur > cr_pri) if (cr_cur is not None and cr_pri is not None) else None
    add_point("Leverage & Liquidity", "F6", "Delta Liquidity", 
              "Current Ratio is higher than in the previous year",
              f"{cr_cur:.2f} vs {cr_pri:.2f}" if f6_passed is not None else "N/A",
              f6_passed)

    # F7: No Dilution
    f7_passed = (shares_cur <= shares_pri) if (shares_cur is not None and shares_pri is not None) else None
    add_point("Leverage & Liquidity", "F7", "No Dilution", 
              "Shares Outstanding stayed the same or decreased",
              f"{shares_cur/1e9:.2f}B vs {shares_pri/1e9:.2f}B" if f7_passed is not None else "N/A",
              f7_passed)

    # ════════════════════════════════════════════════════════════
    # OPERATING EFFICIENCY
    # ════════════════════════════════════════════════════════════

    # F8: Delta Margin
    f8_passed = (margin_cur > margin_pri) if (margin_cur is not None and margin_pri is not None) else None
    add_point("Operating Efficiency", "F8", "Delta Margin", 
              "Net or Gross Margin is higher than in the previous year",
              f"{margin_cur*100:.1f}% vs {margin_pri*100:.1f}%" if f8_passed is not None else "N/A",
              f8_passed)

    # F9: Asset Turnover / Efficiency Proxy (ROIC)
    f9_passed = (roic_cur_final > roic_pri_final) if (roic_cur_final is not None and roic_pri_final is not None) else None
    add_point("Operating Efficiency", "F9", "Capital Efficiency (ROIC)", 
              "ROIC is strictly higher than in the previous year",
              f"{roic_cur_final*100:.1f}% vs {roic_pri_final*100:.1f}%" if f9_passed is not None else "N/A",
              f9_passed)


    # ── Final score ────────────────────────────────────────────────────────────
    if total_score >= 7: label = "Strong"
    elif total_score >= 4: label = "Neutral"
    else: label = "Weak"

    return {
        "score": total_score,
        "max_possible": total_possible,
        "label": label,
        "breakdown": breakdown
    }

def calculate_rule_of_40(metrics):
    """
    SaaS Rule of 40: Revenue Growth + FCF Margin >= 40%
    """
    def safe_float(val, default=0.0):
        if val is None: return default
        try: return float(val)
        except: return default

    # v260: Sync with clean_percent logic to ensure 18.2% instead of 0.18
    rev_growth_raw = safe_float(metrics.get('revenue_growth'))
    # If growth is already scaled (e.g. 18.2), keep it. If decimal (0.18), scale it.
    rev_growth = rev_growth_raw * 100.0 if (0 < abs(rev_growth_raw) < 1.0) else rev_growth_raw
    
    fcf = safe_float(metrics.get('fcf'))
    rev = safe_float(metrics.get('revenue'))
    fcf_margin = (fcf / rev * 100.0) if (fcf and rev and rev > 0) else 0.0
    
    total = rev_growth + fcf_margin
    
    return {
        "revenue_growth": round(rev_growth, 2),
        "fcf_margin": round(fcf_margin, 2),
        "total": round(total, 2),
        "passed": total >= 40,
        "label": "Strong" if total >= 40 else ("Healthy" if total >= 30 else "Weak")
    }

