import re

with open(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\models\scoring.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = '''def calculate_scoring_reform(valuation_data, metrics):
    """
    Evaluates the 'Good to Buy Score' and 'Company Health Score' using a Forward-First approach.
    It categorizes the company into one of 8 specific sectors and applies dynamic templates.
    """
    industry = (metrics.get('industry') or valuation_data.get('industry') or "").lower()
    sector = (metrics.get('sector') or valuation_data.get('sector') or "").lower()
    
    # 1. Sector Definitions
    is_bank = 'bank' in industry or 'credit services' in industry or 'savings' in industry
    is_financial = 'financial' in sector
    is_insurance = 'insurance' in industry
    is_reit = 'real estate' in sector or 'reit' in sector
    is_energy = 'energy' in sector or 'basic materials' in sector or 'materials' in sector
    is_utilities = 'utilities' in sector or 'telecommunication' in sector or 'telecom' in industry
    is_defensive = 'consumer defensive' in sector or 'staples' in sector or 'healthcare' in sector or 'health care' in sector
    is_tech = 'technology' in sector or 'communication services' in sector or 'software' in industry or 'internet' in industry
    # Industrials & Consumer Discretionary is the default fallback if none of the above matches

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
        pts = min(pts, max_pts)
        h_score += pts
        h_breakdown.append({
            "metric": metric,
            "value": format_val(value, is_ratio),
            "points_awarded": int(pts),
            "max_points": int(max_pts)
        })

    def add_b(metric, value, pts, max_pts, is_ratio=True):
        nonlocal b_score
        # Guard clause: Multiples < 0 get 0 points immediately
        if is_ratio == True and value is not None and value < 0:
            pts = 0
        pts = min(pts, max_pts)
        b_score += pts
        b_breakdown.append({
            "metric": metric,
            "value": format_val(value, is_ratio),
            "points_awarded": int(pts),
            "max_points": int(max_pts)
        })

    # 2. Extract Base Metrics
    mos = clean_percent(valuation_data.get('margin_of_safety'))
    
    # Forward-First Growth Fallback
    eps_5yr_g = clean_percent(metrics.get('eps_growth_5y_consensus') or metrics.get('eps_5yr_growth'))
    rev_g = clean_percent(metrics.get('revenue_growth')) # TTM
    # Use 2Y/5Y CAGR if available, else TTM Rev Growth
    fwd_growth = eps_5yr_g if eps_5yr_g > 0 else rev_g
    
    # Forward-First Multiples Fallback
    fwd_pe = clean_ratio(metrics.get('forward_pe'))
    trail_pe = clean_ratio(metrics.get('trailing_pe') or metrics.get('pe_ratio') or metrics.get('current_pe'))
    
    # For Non-GAAP / Tech
    adj_eps = clean_ratio(metrics.get('adjusted_eps'))
    curr_p = clean_ratio(metrics.get('current_price') or valuation_data.get('current_price', 0))
    adj_pe = (curr_p / adj_eps) if (curr_p > 0 and adj_eps > 0) else 0

    # Default P/E logic
    pe = 0
    pe_label = "P/E Ratio"
    
    if is_tech or 'healthcare' in sector:
        if fwd_pe > 0:
            pe = fwd_pe
            pe_label = "P/E Ratio (Fwd)"
        elif adj_pe > 0:
            pe = adj_pe
            pe_label = "P/E Ratio (adj.)"
        else:
            pe = trail_pe
            pe_label = "P/E Ratio (Trailing)"
    else:
        if fwd_pe > 0:
            pe = fwd_pe
            pe_label = "P/E Ratio (Fwd)"
        else:
            pe = trail_pe
            pe_label = "P/E Ratio (Trailing)"

    # Other multiples
    ev_ebitda = clean_ratio(metrics.get('ev_to_ebitda'))
    pb = clean_ratio(metrics.get('price_to_book'))
    ps = clean_ratio(metrics.get('ps_ratio') or metrics.get('price_to_sales'))
    peg_val = clean_ratio(metrics.get('peg_ratio')) # Typically already forward

    def get_mos_points(mos_val, max_pts):
        if mos_val > 15.0: return max_pts
        elif mos_val > 5.0: return max_pts * (14.9 / 25.0)
        elif mos_val >= -5.0: return max_pts * (10.0 / 25.0)
        return 0.0

    # --- ROUTING TO SECTOR TEMPLATES ---
    
    if is_financial and is_bank:
        # Sector 2: Banks & Financials
        nim = clean_percent(metrics.get('nim'))
        add_h("Net Interest Margin", nim, 20 if nim > 3.0 else (10 if nim >= 1.5 else 0), 20, False)
        cet1 = clean_percent(metrics.get('cet1_ratio'))
        add_h("CET1 Ratio", cet1, 20 if cet1 >= 12 else (10 if cet1 >= 10 else 0), 20, False)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 15 else (10 if roe >= 8 else 0), 20, False)
        roa = clean_percent(metrics.get('roa'))
        add_h("ROA", roa, 20 if roa >= 1.0 else (10 if roa >= 0.5 else 0), 20, False) # v72: Updated ROA threshold
        bvps = clean_percent(metrics.get('bvps_growth'))
        add_h("BVPS Growth", bvps, 20 if bvps > 8 else (10 if bvps >= 3 else 0), 20, False)
        
        add_b("Margin of Safety (DDM)", mos, get_mos_points(mos, 25), 25, False)
        add_b("Next 2-5Y EPS Growth", fwd_growth, 10 if fwd_growth > 10 else (5 if fwd_growth >= 5 else 0), 10, False)
        pts = 20 if (0 < pe <= 13) else (10 if pe <= 15 else 0)
        add_b(pe_label, pe, pts, 20, True)
        pts = 20 if (0 < pb < 1.5) else (10 if pb <= 2.0 else 0)
        add_b("Price-to-Book", pb, pts, 20, True)
        div_y = clean_percent(metrics.get('fwd_dividend_yield') or metrics.get('dividend_yield'))
        add_b("Fwd Dividend Yield", div_y, 15 if div_y > 4 else (7.5 if div_y >= 2 else 0), 15, False)
        add_b("PEG Ratio (Fwd)", peg_val, 10 if (0 < peg_val < 1.0) else (5 if (0 < peg_val <= 1.5) else 0), 10, True)

    elif is_insurance:
        # Sector 3: Insurance
        nim = clean_percent(metrics.get('nim'))
        add_h("Float / Net Interest", nim, 20 if nim > 3.0 else (10 if nim >= 1.5 else 0), 20, False)
        de = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Debt-to-Equity", de, 20 if (0 <= de < 1.0) else (10 if de < 2.0 else 0), 20, True)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 12 else (10 if roe >= 8 else 0), 20, False)
        roa = clean_percent(metrics.get('roa'))
        add_h("ROA", roa, 20 if roa >= 1.0 else (10 if roa >= 0.5 else 0), 20, False)
        bvps = clean_percent(metrics.get('bvps_growth'))
        add_h("BVPS Growth", bvps, 20 if bvps > 8 else (10 if bvps >= 3 else 0), 20, False)
        
        add_b("Margin of Safety", mos, get_mos_points(mos, 30), 30, False)
        pts = 20 if (0 < pe <= 15) else (10 if pe <= 18 else 0)
        add_b(pe_label, pe, pts, 20, True)
        pts = 25 if (0 < pb < 1.5) else (12.5 if pb <= 2.0 else 0)
        add_b("Price-to-Book", pb, pts, 25, True)
        div_y = clean_percent(metrics.get('fwd_dividend_yield') or metrics.get('dividend_yield'))
        add_b("Fwd Dividend Yield", div_y, 15 if div_y > 3 else (7.5 if div_y >= 1.5 else 0), 15, False)
        add_b("Next 2-5Y EPS Growth", fwd_growth, 10 if fwd_growth > 8 else (5 if fwd_growth >= 4 else 0), 10, False)

    elif is_reit:
        # Sector 4: Real Estate / REITs
        de = clean_ratio(metrics.get('debt_to_ebitda') or (clean_ratio(metrics.get('total_debt')) / clean_ratio(metrics.get('ebitda')) if clean_ratio(metrics.get('ebitda')) > 0 else 0))
        # REITs can safely handle up to 6.0x Debt/EBITDA
        add_h("Debt-to-EBITDA", de, 25 if (0 <= de < 6.0) else (12.5 if de <= 7.5 else 0), 25, True)
        add_h("Interest Coverage", clean_ratio(metrics.get('interest_coverage')), 25 if clean_ratio(metrics.get('interest_coverage')) > 3.0 else (12.5 if clean_ratio(metrics.get('interest_coverage')) >= 1.5 else 0), 25, True)
        add_h("Current Ratio", clean_ratio(metrics.get('current_ratio')), 25 if clean_ratio(metrics.get('current_ratio')) >= 0.8 else 0, 25, True)
        div_track = metrics.get('dividend_streak', 0)
        add_h("Dividend Track Record", div_track, 25 if div_track > 10 else (12.5 if div_track >= 5 else 0), 25, "raw")
        
        add_b("Margin of Safety (NAV)", mos, get_mos_points(mos, 30), 30, False)
        affo_g = clean_percent(metrics.get('affo_growth') or fwd_growth)
        add_b("Next 1-3Y AFFO Growth", affo_g, 20 if affo_g > 8 else (10 if affo_g >= 3 else 0), 20, False)
        
        p_affo = clean_ratio(metrics.get('price_to_affo'))
        if p_affo <= 0: p_affo = pe # Fallback if AFFO missing
        pts = 20 if (0 < p_affo <= 15) else (10 if p_affo <= 18 else 0)
        add_b("P/AFFO (Fwd)", p_affo, pts, 20, True)
        
        affo_yield = clean_percent(metrics.get('affo_yield'))
        if affo_yield <= 0: affo_yield = clean_percent(metrics.get('fcf_yield'))
        add_b("Fwd AFFO Yield", affo_yield, 15 if affo_yield > 8 else (7.5 if affo_yield >= 5 else 0), 15, False)
        
        div_y = clean_percent(metrics.get('fwd_dividend_yield') or metrics.get('dividend_yield'))
        add_b("Fwd Dividend Yield", div_y, 15 if div_y > 5 else (7.5 if div_y >= 3 else 0), 15, False)

    elif is_energy:
        # Sector 5: Energy & Materials
        de = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Debt-to-Equity", de, 20 if (0 <= de < 0.6) else (10 if de < 1.0 else 0), 20, True)
        cr = clean_ratio(metrics.get('current_ratio'))
        add_h("Current Ratio", cr, 20 if cr >= 1.5 else (10 if cr >= 1.0 else 0), 20, True)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 15 else (10 if roe >= 8 else 0), 20, False)
        roic = clean_percent(metrics.get('roic'))
        add_h("ROIC", roic, 25 if roic > 12 else (12.5 if roic >= 7 else 0), 25, False)
        fcf_trend = metrics.get('fcf_trend', 'Flat')
        add_h("FCF Trend", fcf_trend, 15 if fcf_trend == "Growing" else 0, 15, "raw")
        
        add_b("Margin of Safety", mos, get_mos_points(mos, 30), 30, False)
        # EV/EBITDA is king for energy
        pts = 20 if (0 < ev_ebitda <= 6.0) else (10 if ev_ebitda <= 9.0 else 0)
        add_b("EV / EBITDA (Fwd)", ev_ebitda, pts, 20, True)
        # Inverted P/E logic for cyclical tops
        pts = 0
        if pe > 0:
            if pe < 6: pts = 5 # Value trap / Peak cycle
            elif 6 <= pe <= 15: pts = 15 # Healthy cycle
            elif 15 < pe <= 20: pts = 10
        add_b(pe_label, pe, pts, 15, True)
        
        pts = 20 if (0 < pb <= 1.5) else (10 if pb <= 2.5 else 0)
        add_b("Price-to-Book", pb, pts, 20, True)
        
        div_y = clean_percent(metrics.get('fwd_dividend_yield') or metrics.get('dividend_yield'))
        add_b("Fwd Dividend Yield", div_y, 15 if div_y > 4 else (7.5 if div_y >= 2 else 0), 15, False)

    elif is_utilities:
        # Sector 6: Utilities & Telecom
        de = clean_ratio(metrics.get('debt_to_equity'))
        # High leverage tolerated
        add_h("Debt-to-Equity", de, 20 if (0 <= de <= 2.0) else (10 if de <= 3.0 else 0), 20, True)
        cr = clean_ratio(metrics.get('current_ratio'))
        add_h("Current Ratio", cr, 20 if cr >= 0.7 else (10 if cr >= 0.5 else 0), 20, True)
        ic = clean_ratio(metrics.get('interest_coverage'))
        add_h("Interest Coverage", ic, 20 if ic > 3.0 else (10 if ic >= 1.5 else 0), 20, True)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 10 else (10 if roe >= 6 else 0), 20, False)
        roic = clean_percent(metrics.get('roic'))
        add_h("ROIC", roic, 20 if roic > 6 else (10 if roic >= 4 else 0), 20, False)
        
        add_b("Margin of Safety", mos, get_mos_points(mos, 30), 30, False)
        add_b("Next 2-5Y EPS Growth", fwd_growth, 10 if fwd_growth > 5 else (5 if fwd_growth >= 2 else 0), 10, False)
        pts = 15 if (0 < pe <= 15) else (7.5 if pe <= 18 else 0)
        add_b(pe_label, pe, pts, 15, True)
        # EV/EBITDA isolates high D&A
        pts = 20 if (0 < ev_ebitda <= 10.0) else (10 if ev_ebitda <= 14.0 else 0)
        add_b("EV / EBITDA (Fwd)", ev_ebitda, pts, 20, True)
        div_y = clean_percent(metrics.get('fwd_dividend_yield') or metrics.get('dividend_yield'))
        add_b("Fwd Dividend Yield", div_y, 25 if div_y > 4 else (12.5 if div_y >= 2.5 else 0), 25, False)

    elif is_defensive:
        # Sector 7: Defensive / Healthcare
        de = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Debt-to-Equity", de, 20 if (0 <= de < 1.0) else (10 if de < 1.5 else 0), 20, True)
        cr = clean_ratio(metrics.get('current_ratio'))
        add_h("Current Ratio", cr, 20 if cr >= 1.2 else (10 if cr >= 0.9 else 0), 20, True)
        ic = clean_ratio(metrics.get('interest_coverage'))
        add_h("Interest Coverage", ic, 20 if ic > 5.0 else (10 if ic >= 3.0 else 0), 20, True)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 15 else (10 if roe >= 10 else 0), 20, False)
        roic = clean_percent(metrics.get('roic'))
        add_h("ROIC", roic, 20 if roic > 12 else (10 if roic >= 8 else 0), 20, False)
        
        add_b("Margin of Safety", mos, get_mos_points(mos, 30), 30, False)
        add_b("Next 2-5Y EPS Growth", fwd_growth, 15 if fwd_growth > 8 else (7.5 if fwd_growth >= 4 else 0), 15, False)
        # Premium tolerated
        pts = 20 if (0 < pe <= 20) else (10 if pe <= 25 else 0)
        if pts == 0 and pe > 0 and 0 < peg_val <= 1.2 and fwd_growth >= 15.0: pts = 10 # Growth Override
        add_b(pe_label, pe, pts, 20, True)
        pts = 15 if (0 < ev_ebitda <= 14.0) else (7.5 if ev_ebitda <= 18.0 else 0)
        if pts == 0 and ev_ebitda > 0 and 0 < peg_val <= 1.2 and fwd_growth >= 15.0: pts = 7.5 # Growth Override
        add_b("EV / EBITDA (Fwd)", ev_ebitda, pts, 15, True)
        add_b("PEG Ratio (Fwd)", peg_val, 20 if (0 < peg_val < 1.5) else (10 if peg_val <= 2.0 else 0), 20, True)

    elif is_tech:
        # Sector 1: Technology & Software
        de = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Debt-to-Equity", de, 20 if (0 <= de < 0.5) else (10 if de < 1.0 else 0), 20, True)
        cr = clean_ratio(metrics.get('current_ratio'))
        add_h("Current Ratio", cr, 20 if cr >= 1.5 else (10 if cr >= 1.0 else 0), 20, True)
        ic = clean_ratio(metrics.get('interest_coverage'))
        add_h("Interest Coverage", ic, 20 if ic > 5.0 else (10 if ic >= 3.0 else 0), 20, True)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 15 else (10 if roe >= 10 else 0), 20, False)
        roic = clean_percent(metrics.get('roic'))
        add_h("ROIC", roic, 20 if roic > 15 else (10 if roic >= 10 else 0), 20, False)
        
        add_b("Margin of Safety (DCF)", mos, get_mos_points(mos, 30), 30, False)
        add_b("Next 2-5Y Rev Growth", fwd_growth, 20 if fwd_growth > 15 else (10 if fwd_growth >= 8 else 0), 20, False)
        
        target_pe = 25.0
        pts = 20 if (0 < pe <= target_pe) else (10 if pe <= target_pe * 1.3 else 0)
        if pts == 0 and pe > 0 and 0 < peg_val <= 1.2 and fwd_growth >= 20.0: pts = 10 # Growth Override
        add_b(pe_label, pe, pts, 20, True)
        
        pts = 10 if (0 < ev_ebitda <= 18.0) else (5 if ev_ebitda <= 25.0 else 0)
        if pts == 0 and ev_ebitda > 0 and 0 < peg_val <= 1.2 and fwd_growth >= 20.0: pts = 5 # Growth Override
        add_b("EV / EBITDA (Fwd)", ev_ebitda, pts, 10, True)
        
        add_b("PEG Ratio (Fwd)", peg_val, 10 if (0 < peg_val < 1.5) else (5 if peg_val <= 2.0 else 0), 10, True)
        
        margin = clean_percent(metrics.get('ebit_margin') or metrics.get('operating_margin'))
        target_ps = target_pe * (margin / 100.0)
        pts = 0
        if ps > 0:
            if margin < 0:
                if fwd_growth > 20 and ps <= 5.0: pts = 5
            else:
                if ps <= target_ps: pts = 10
                elif ps <= target_ps * 1.5: pts = 5
        add_b("P/S Ratio", ps, pts, 10, True)

    else:
        # Sector 8: Industrials & Consumer Discretionary (Default fallback)
        de = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Debt-to-Equity", de, 20 if (0 <= de < 1.0) else (10 if de < 1.5 else 0), 20, True)
        cr = clean_ratio(metrics.get('current_ratio'))
        add_h("Current Ratio", cr, 20 if cr >= 1.2 else (10 if cr >= 1.0 else 0), 20, True)
        ic = clean_ratio(metrics.get('interest_coverage'))
        add_h("Interest Coverage", ic, 20 if ic > 4.0 else (10 if ic >= 2.0 else 0), 20, True)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 12 else (10 if roe >= 8 else 0), 20, False)
        roic = clean_percent(metrics.get('roic'))
        add_h("ROIC", roic, 20 if roic > 10 else (10 if roic >= 6 else 0), 20, False)
        
        add_b("Margin of Safety", mos, get_mos_points(mos, 30), 30, False)
        add_b("Next 2-5Y Rev Growth", fwd_growth, 20 if fwd_growth > 10 else (10 if fwd_growth >= 5 else 0), 20, False)
        
        pts = 20 if (0 < pe <= 18) else (10 if pe <= 22 else 0)
        if pts == 0 and pe > 0 and 0 < peg_val <= 1.2 and fwd_growth >= 15.0: pts = 10 # Growth Override
        add_b(pe_label, pe, pts, 20, True)
        
        pts = 10 if (0 < ev_ebitda <= 12.0) else (5 if ev_ebitda <= 16.0 else 0)
        if pts == 0 and ev_ebitda > 0 and 0 < peg_val <= 1.2 and fwd_growth >= 15.0: pts = 5 # Growth Override
        add_b("EV / EBITDA (Fwd)", ev_ebitda, pts, 10, True)
        
        pts = 10 if (0 < pb <= 2.0) else (5 if pb <= 3.0 else 0)
        add_b("Price-to-Book", pb, pts, 10, True)
        
        add_b("PEG Ratio (Fwd)", peg_val, 10 if (0 < peg_val < 1.0) else (5 if peg_val <= 1.5 else 0), 10, True)

    return {
        "health_score_total": min(int(h_score), 100),
        "good_to_buy_total": min(int(b_score), 100),
        "health_breakdown": h_breakdown,
        "buy_breakdown": b_breakdown
    }'''

pattern = r'def calculate_scoring_reform\(valuation_data, metrics\):.*?return \{\n\s+"health_score_total":.*?\n\s+"good_to_buy_total":.*?\n\s+"health_breakdown":.*?\n\s+"buy_breakdown": b_breakdown\n\s+\}'
new_content = re.sub(pattern, new_func, content, flags=re.DOTALL)

with open(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\models\scoring.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Updated scoring.py")
