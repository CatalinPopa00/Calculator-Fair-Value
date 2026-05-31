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
def get_target_pe(sector, industry):
    s_low = str(sector).lower()
    i_low = str(industry).lower()
    if 'technology' in s_low or 'software' in i_low or 'communication' in s_low: return 25.0
    if 'consumer discretionary' in s_low: return 22.0
    if 'health' in s_low or 'biotech' in i_low: return 18.0
    if any(x in s_low for x in ['industrials', 'materials', 'consumer staples', 'defensive']): return 16.0
    if any(x in s_low for x in ['utilities', 'real estate', 'reit']): return 15.0
    if 'financial' in s_low or 'bank' in i_low: return 13.0
    return 18.0

def clean_ratio(val):
    if val is None: return 0.0
    if isinstance(val, str):
        val = val.replace('%', '').replace('x', '').replace('$', '').replace(',', '')
    try: return float(val)
    except: return 0.0

class DefaultScoringStrategy:
    def eval_debt_to_equity(self, de, metrics):
        pts = 20 if de < 0.8 else (10 if de <= 1.5 else 0)
        return pts, 20

    def eval_current_ratio(self, cr, metrics, cr_exempt, fcf_trend):
        fcf_val = clean_ratio(metrics.get('fcf'))
        pts = 0
        if cr >= 1.5:
            pts = 15
        elif 0.7 <= cr < 1.5:
            if cr_exempt or fcf_trend == "Growing":
                pts = 15
            else:
                pts = 7.5
        else:
            if cr_exempt and fcf_val > 0:
                pts = 7.5
            else:
                pts = 0
        return pts, 15

    def eval_ebit_margin(self, ebit_m):
        pts = 15 if ebit_m > 20 else (7.5 if ebit_m >= 10 else 0)
        return pts, 15

    def eval_roic(self, roic, metrics):
        pts = 20 if roic > 15 else (10 if roic >= 8 else 0)
        return "ROIC", roic, pts, 20

    def eval_pe_ratio(self, pe, target_pe, metrics):
        pts = 0
        if pe > 0:
            if pe <= target_pe:
                pts = 20
            elif pe <= target_pe * 1.3:
                peg_val = clean_ratio(metrics.get('peg_ratio'))
                rev_g_val = clean_percent(metrics.get('revenue_growth'))
                if rev_g_val > 15 or (0 < peg_val < 1.5):
                    pts = 15
                else:
                    pts = 10
        return pts, 20

class UtilitiesStrategy(DefaultScoringStrategy):
    def eval_debt_to_equity(self, de, metrics):
        pts = 20 if de <= 2.0 else (10 if de <= 3.0 else 0)
        return pts, 20

    def eval_current_ratio(self, cr, metrics, cr_exempt, fcf_trend):
        pts = 15 if cr >= 0.5 else 0
        return pts, 15

    def eval_roic(self, roic, metrics):
        roe = clean_percent(metrics.get('roe'))
        pts = 20 if roe >= 8 else (10 if roe >= 5 else 0)
        return "ROE", roe, pts, 20

class RetailStrategy(DefaultScoringStrategy):
    def eval_debt_to_equity(self, de, metrics):
        roic = clean_percent(metrics.get('roic'))
        fcf_trend = metrics.get('fcf_trend', 'Flat')
        equity = metrics.get('total_equity', 1) 
        if (de > 3.0 or de < 0 or equity < 0) and roic > 15 and fcf_trend == "Growing":
            return 20, 20
        return super().eval_debt_to_equity(de, metrics)

    def eval_ebit_margin(self, ebit_m):
        pts = 15 if ebit_m >= 10 else (7.5 if ebit_m >= 5 else 0)
        return pts, 15

class EnergyStrategy(DefaultScoringStrategy):
    def eval_ebit_margin(self, ebit_m):
        pts = 15 if ebit_m >= 8 else (7.5 if ebit_m >= 4 else 0)
        return pts, 15

    def eval_pe_ratio(self, pe, target_pe, metrics):
        pts = 0
        if pe > 0:
            if pe <= 12:
                pts = 20
            elif pe <= 15:
                pts = 10
        return pts, 20

class HealthcareStrategy(DefaultScoringStrategy):
    def eval_current_ratio(self, cr, metrics, cr_exempt, fcf_trend):
        if cr >= 1.0:
            pts = 15
        elif cr >= 0.8:
            pts = 10
        else:
            pts = 0
        return pts, 15

class IndustrialsStrategy(DefaultScoringStrategy):
    def eval_ebit_margin(self, ebit_m):
        pts = 15 if ebit_m >= 8 else (7 if ebit_m >= 5 else 0)
        return pts, 15

def get_scoring_strategy(sector, industry):
    s_low = str(sector).lower()
    i_low = str(industry).lower()
    if 'utilities' in s_low:
        return UtilitiesStrategy()
    elif 'consumer discretionary' in s_low or 'retail' in i_low:
        return RetailStrategy()
    elif 'energy' in s_low:
        return EnergyStrategy()
    elif 'health' in s_low or 'biotech' in i_low:
        return HealthcareStrategy()
    elif 'industrials' in s_low or 'defense' in i_low or 'aerospace' in i_low:
        return IndustrialsStrategy()
    return DefaultScoringStrategy()

def calculate_scoring_reform(valuation_data, metrics):
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
    is_tech = 'technology' in sector or 'communication services' in sector or 'software' in industry or 'internet' in industry or 'information services' in industry

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
            "points_awarded": float(pts),
            "max_points": int(max_pts)
        })

    def add_b(metric, value, pts, max_pts, is_ratio=True):
        nonlocal b_score
        if is_ratio == True and value is not None and value < 0:
            pts = 0
        pts = min(pts, max_pts)
        b_score += pts
        b_breakdown.append({
            "metric": metric,
            "value": format_val(value, is_ratio),
            "points_awarded": float(pts),
            "max_points": int(max_pts)
        })

    def get_mos_points(mos_val, max_pts):
        if mos_val > 15.0: return max_pts
        elif mos_val > 5.0: return max_pts * (14.9 / 25.0)
        elif mos_val >= -5.0: return max_pts * (10.0 / 25.0)
        return 0.0

    def get_rel_pts(val, median, max_pts, lower_is_better=True):
        """Dynamic Sector Comparison. Returns max_pts if <= median, half if <= median*1.3, else 0."""
        if val is None or val <= 0: return 0
        if median is None or median <= 0:
            # Fallback if sector median is missing or invalid
            if lower_is_better:
                if val <= 15: return max_pts
                elif val <= 25: return max_pts / 2.0
                return 0
            else:
                if val >= 10: return max_pts
                elif val >= 5: return max_pts / 2.0
                return 0
            
        if lower_is_better:
            if val <= median: return max_pts
            elif val <= median * 1.3: return max_pts / 2.0
            return 0
        else:
            if val >= median: return max_pts
            elif val >= median * 0.7: return max_pts / 2.0
            return 0

    # 2. Extract Base Metrics
    mos = clean_percent(valuation_data.get('margin_of_safety'))
    
    # Sector Medians
    sec_pe = clean_ratio(valuation_data.get('sector_median_pe'))
    sec_ps = clean_ratio(valuation_data.get('sector_median_ps'))
    sec_pb = clean_ratio(valuation_data.get('sector_median_pb'))
    sec_ev_ebitda = clean_ratio(valuation_data.get('sector_median_ev_ebitda'))
    sec_peg = clean_ratio(valuation_data.get('sector_median_peg'))
    
    # Strictly 2-Year CAGR for Growth
    eps_2y_g = clean_percent(metrics.get('eps_growth'))
    rev_2y_g = clean_percent(metrics.get('rev_cagr_2y')) or clean_percent(metrics.get('revenue_growth'))
    
    # Strict Forward 1Y Multiples
    fwd_pe = clean_ratio(metrics.get('forward_pe') or metrics.get('fwd_pe'))
    ev_ebitda = clean_ratio(metrics.get('forward_ev_ebitda') or metrics.get('ev_to_ebitda'))
    ps = clean_ratio(metrics.get('forward_ev_sales') or metrics.get('fwd_ps') or metrics.get('ps_ratio'))
    pb = clean_ratio(metrics.get('price_to_book'))
    
    # Calculate Hybrid PEG: Fwd PE 1Y / 2Y EPS Growth CAGR
    hybrid_peg = 0.0
    growth_rate = rev_2y_g if rev_2y_g > 0 else eps_2y_g
    if fwd_pe > 0 and growth_rate > 0:
        # User requested: (Forward P/E 1Y) / (Forward Growth Rate * 100)
        # Note: clean_percent returns 15.0 for 15%.
        # If it returns 15.0, dividing by 15.0 is the same as PE / (0.15 * 100).
        # We explicitly enforce the logic mathematically as PE / (growth * 100) assuming growth is decimal.
        # But since clean_percent scales decimals < 10.0 by 100, we check:
        actual_growth_pct = growth_rate * 100.0 if growth_rate < 1.0 else growth_rate
        hybrid_peg = fwd_pe / actual_growth_pct
    
    pe = fwd_pe
    pe_label = "P/E Ratio (1Y Fwd)"
    if pe <= 0:
        pe = clean_ratio(metrics.get('trailing_pe') or metrics.get('current_pe'))
        pe_label = "P/E Ratio (TTM)"
        
    peg_val = hybrid_peg if hybrid_peg > 0 else clean_ratio(metrics.get('peg_ratio'))

    # --- ROUTING TO SECTOR TEMPLATES ---
    
    if is_financial and is_bank:
        nim = clean_percent(metrics.get('nim'))
        add_h("Net Interest Margin", nim, 20 if nim > 3.0 else (10 if nim >= 1.5 else 0), 20, False)
        cet1 = clean_percent(metrics.get('cet1_ratio'))
        add_h("CET1 Ratio", cet1, 20 if cet1 >= 12 else (10 if cet1 >= 10 else 0), 20, False)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 15 else (10 if roe >= 8 else 0), 20, False)
        roa = clean_percent(metrics.get('roa'))
        add_h("ROA", roa, 20 if roa >= 1.0 else (10 if roa >= 0.5 else 0), 20, False)
        bvps = clean_percent(metrics.get('bvps_growth'))
        add_h("BVPS Growth", bvps, 20 if bvps > 8 else (10 if bvps >= 3 else 0), 20, False)
        
        add_b("Margin of Safety (DDM)", mos, get_mos_points(mos, 25), 25, False)
        add_b("EPS Growth (Fwd)", eps_2y_g, 10 if eps_2y_g > 10 else (5 if eps_2y_g >= 5 else 0), 10, False)
        add_b(pe_label, pe, get_rel_pts(pe, sec_pe, 20), 20, True)
        add_b("Price-to-Book", pb, get_rel_pts(pb, sec_pb, 20), 20, True)
        div_y = clean_percent(metrics.get('fwd_dividend_yield') or metrics.get('dividend_yield'))
        add_b("Dividend Yield (Fwd)", div_y, 15 if div_y > 4 else (7.5 if div_y >= 2 else 0), 15, False)
        add_b("PEG Ratio (Fwd)", peg_val, get_rel_pts(peg_val, sec_peg, 10), 10, True)

    elif is_insurance:
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
        add_b(pe_label, pe, get_rel_pts(pe, sec_pe, 20), 20, True)
        add_b("Price-to-Book", pb, get_rel_pts(pb, sec_pb, 25), 25, True)
        div_y = clean_percent(metrics.get('fwd_dividend_yield') or metrics.get('dividend_yield'))
        add_b("Dividend Yield (Fwd)", div_y, 15 if div_y > 3 else (7.5 if div_y >= 1.5 else 0), 15, False)
        add_b("EPS Growth (Fwd)", eps_2y_g, 10 if eps_2y_g > 8 else (5 if eps_2y_g >= 4 else 0), 10, False)

    elif is_reit:
        de = clean_ratio(metrics.get('debt_to_ebitda') or (clean_ratio(metrics.get('total_debt')) / clean_ratio(metrics.get('ebitda')) if clean_ratio(metrics.get('ebitda')) > 0 else 0))
        add_h("Debt-to-EBITDA", de, 25 if (0 <= de < 6.0) else (12.5 if de <= 7.5 else 0), 25, True)
        add_h("Interest Coverage", clean_ratio(metrics.get('interest_coverage')), 25 if clean_ratio(metrics.get('interest_coverage')) > 3.0 else (12.5 if clean_ratio(metrics.get('interest_coverage')) >= 1.5 else 0), 25, True)
        add_h("Current Ratio", clean_ratio(metrics.get('current_ratio')), 25 if clean_ratio(metrics.get('current_ratio')) >= 0.8 else 0, 25, True)
        div_track = metrics.get('dividend_streak', 0)
        add_h("Dividend Track Record", div_track, 25 if div_track > 10 else (12.5 if div_track >= 5 else 0), 25, "raw")
        
        add_b("Margin of Safety (NAV)", mos, get_mos_points(mos, 30), 30, False)
        affo_g = clean_percent(metrics.get('affo_growth') or eps_2y_g)
        add_b("AFFO Growth (Fwd)", affo_g, 20 if affo_g > 8 else (10 if affo_g >= 3 else 0), 20, False)
        
        p_affo = clean_ratio(metrics.get('price_to_affo'))
        if p_affo <= 0: p_affo = pe # Fallback
        # We don't have sec_p_affo, so we compare P/AFFO with Sector PE proxy
        add_b("P/AFFO (Fwd)", p_affo, get_rel_pts(p_affo, sec_pe, 20), 20, True)
        
        affo_yield = clean_percent(metrics.get('affo_yield'))
        if affo_yield <= 0: affo_yield = clean_percent(metrics.get('fcf_yield'))
        add_b("AFFO Yield (Fwd)", affo_yield, 15 if affo_yield > 8 else (7.5 if affo_yield >= 5 else 0), 15, False)
        
        div_y = clean_percent(metrics.get('fwd_dividend_yield') or metrics.get('dividend_yield'))
        add_b("Dividend Yield (Fwd)", div_y, 15 if div_y > 5 else (7.5 if div_y >= 3 else 0), 15, False)

    elif is_energy:
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
        add_b("EV/EBITDA (1Y Fwd)", ev_ebitda, get_rel_pts(ev_ebitda, sec_ev_ebitda, 20), 20, True)
        
        # Inverted P/E logic for cyclical tops is kept absolute, or maybe relative inverted?
        # Energy: low P/E might be a trap. If we use relative, it might break cyclical logic.
        # But we must apply sector logic. Let's use get_rel_pts with lower_is_better.
        add_b(pe_label, pe, get_rel_pts(pe, sec_pe, 15), 15, True)
        
        add_b("Price-to-Book", pb, get_rel_pts(pb, sec_pb, 20), 20, True)
        div_y = clean_percent(metrics.get('fwd_dividend_yield') or metrics.get('dividend_yield'))
        add_b("Dividend Yield (Fwd)", div_y, 15 if div_y > 4 else (7.5 if div_y >= 2 else 0), 15, False)

    elif is_utilities:
        de = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Debt-to-Equity", de, 20 if (0 <= de <= 2.0) else (10 if de <= 3.0 else 0), 20, True)
        cr = clean_ratio(metrics.get('current_ratio'))
        add_h("Current Ratio", cr, 20 if cr >= 0.7 else (10 if cr >= 0.5 else 0), 20, True)
        ic = clean_ratio(metrics.get('interest_coverage'))
        de_for_ic = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Interest Coverage", ic, 20 if de_for_ic == 0 else (20 if ic > 3.0 else (10 if ic >= 1.5 else 0)), 20, True)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 10 else (10 if roe >= 6 else 0), 20, False)
        roic = clean_percent(metrics.get('roic'))
        add_h("ROIC", roic, 20 if roic > 6 else (10 if roic >= 4 else 0), 20, False)
        
        add_b("Margin of Safety", mos, get_mos_points(mos, 30), 30, False)
        add_b("EPS Growth (Fwd)", eps_2y_g, 10 if eps_2y_g > 5 else (5 if eps_2y_g >= 2 else 0), 10, False)
        add_b(pe_label, pe, get_rel_pts(pe, sec_pe, 15), 15, True)
        add_b("EV/EBITDA (1Y Fwd)", ev_ebitda, get_rel_pts(ev_ebitda, sec_ev_ebitda, 20), 20, True)
        div_y = clean_percent(metrics.get('fwd_dividend_yield') or metrics.get('dividend_yield'))
        add_b("Dividend Yield (Fwd)", div_y, 25 if div_y > 4 else (12.5 if div_y >= 2.5 else 0), 25, False)

    elif is_defensive:
        de = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Debt-to-Equity", de, 20 if (0 <= de < 1.0) else (10 if de < 1.5 else 0), 20, True)
        cr = clean_ratio(metrics.get('current_ratio'))
        add_h("Current Ratio", cr, 20 if cr >= 1.2 else (10 if cr >= 0.9 else 0), 20, True)
        ic = clean_ratio(metrics.get('interest_coverage'))
        de_for_ic = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Interest Coverage", ic, 20 if de_for_ic == 0 else (20 if ic > 5.0 else (10 if ic >= 3.0 else 0)), 20, True)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 15 else (10 if roe >= 10 else 0), 20, False)
        roic = clean_percent(metrics.get('roic'))
        add_h("ROIC", roic, 20 if roic > 12 else (10 if roic >= 8 else 0), 20, False)
        
        add_b("Margin of Safety", mos, get_mos_points(mos, 30), 30, False)
        add_b("EPS Growth (Fwd)", eps_2y_g, 15 if eps_2y_g > 8 else (7.5 if eps_2y_g >= 4 else 0), 15, False)
        
        pts = get_rel_pts(pe, sec_pe, 20)
        if pts == 0 and pe > 0 and 0 < peg_val <= 1.2 and eps_2y_g >= 15.0: pts = 10 # Growth Override
        add_b(pe_label, pe, pts, 20, True)
        
        pts = get_rel_pts(ev_ebitda, sec_ev_ebitda, 15)
        if pts == 0 and ev_ebitda > 0 and 0 < peg_val <= 1.2 and eps_2y_g >= 15.0: pts = 7.5 # Growth Override
        add_b("EV/EBITDA (1Y Fwd)", ev_ebitda, pts, 15, True)
        add_b("PEG Ratio (Fwd)", peg_val, get_rel_pts(peg_val, sec_peg, 20), 20, True)

    elif is_tech:
        de = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Debt-to-Equity", de, 20 if (0 <= de <= 1.0) else (10 if de <= 2.0 else 0), 20, True)
        cr = clean_ratio(metrics.get('current_ratio'))
        add_h("Current Ratio", cr, 20 if cr >= 1.0 else (10 if cr >= 0.8 else 0), 20, True)
        ic = clean_ratio(metrics.get('interest_coverage'))
        de_for_ic = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Interest Coverage", ic, 20 if de_for_ic == 0 else (20 if ic > 5.0 else (10 if ic >= 3.0 else 0)), 20, True)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 15 else (10 if roe >= 10 else 0), 20, False)
        roic = clean_percent(metrics.get('roic'))
        add_h("ROIC", roic, 20 if roic > 15 else (10 if roic >= 10 else 0), 20, False)
        
        add_b("Margin of Safety (DCF)", mos, get_mos_points(mos, 30), 30, False)
        add_b("Revenue Growth (2y Avg Fwd)", rev_2y_g, 20 if rev_2y_g > 15 else (10 if rev_2y_g >= 8 else 0), 20, False)
        
        pts = get_rel_pts(pe, sec_pe, 20)
        if pts == 0 and pe > 0 and 0 < peg_val <= 1.2 and rev_2y_g >= 20.0: pts = 10 # Growth Override
        add_b(pe_label, pe, pts, 20, True)
        
        pts = get_rel_pts(ev_ebitda, sec_ev_ebitda, 10)
        if pts == 0 and ev_ebitda > 0 and 0 < peg_val <= 1.2 and rev_2y_g >= 20.0: pts = 5 # Growth Override
        add_b("EV/EBITDA (1Y Fwd)", ev_ebitda, pts, 10, True)
        
        add_b("PEG Ratio (Fwd)", peg_val, get_rel_pts(peg_val, sec_peg, 10), 10, True)
        
        # P/S Ratio
        add_b("P/S Ratio (1Y Fwd)", ps, get_rel_pts(ps, sec_ps, 10), 10, True)

    else:
        # Sector 8: Industrials & Consumer Discretionary
        de = clean_ratio(metrics.get('debt_to_equity'))
        de_pts = 0
        if 0 <= de < 1.0:
            de_pts = 20
        elif 0 <= de < 1.5:
            de_pts = 10
        elif de < 0:
            ic_check = clean_ratio(metrics.get('interest_coverage'))
            de_pts = 20 if ic_check > 4.0 else 0
        add_h("Debt-to-Equity", de, de_pts, 20, True)
        
        cr = clean_ratio(metrics.get('current_ratio'))
        add_h("Current Ratio", cr, 20 if cr >= 1.2 else (10 if cr >= 1.0 else 0), 20, True)
        ic = clean_ratio(metrics.get('interest_coverage'))
        de_for_ic = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Interest Coverage", ic, 20 if de_for_ic == 0 else (20 if ic > 4.0 else (10 if ic >= 2.0 else 0)), 20, True)
        
        roe = clean_percent(metrics.get('roe'))
        roic = clean_percent(metrics.get('roic'))
        if roe < 0:
            add_h("ROE", roe, 0, 20, False)
        else:
            add_h("ROE", roe, 20 if roe > 12 else (10 if roe >= 8 else 0), 20, False)
            
        add_h("ROIC", roic, 20 if roic > 10 else (10 if roic >= 6 else 0), 20, False)
        
        add_b("Margin of Safety", mos, get_mos_points(mos, 30), 30, False)
        add_b("Revenue Growth (2y Avg Fwd)", rev_2y_g, 20 if rev_2y_g > 10 else (10 if rev_2y_g >= 5 else 0), 20, False)
        
        pts = get_rel_pts(pe, sec_pe, 20)
        if pts == 0 and pe > 0 and 0 < peg_val <= 1.2 and rev_2y_g >= 15.0: pts = 10 # Growth Override
        add_b(pe_label, pe, pts, 20, True)
        
        pts = get_rel_pts(ev_ebitda, sec_ev_ebitda, 15)
        if pts == 0 and ev_ebitda > 0 and 0 < peg_val <= 1.2 and rev_2y_g >= 15.0: pts = 7.5 # Growth Override
        add_b("EV/EBITDA (1Y Fwd)", ev_ebitda, pts, 15, True)
        
        add_b("PEG Ratio (Fwd)", peg_val, get_rel_pts(peg_val, sec_peg, 15), 15, True)

    return {
        "health_score_total": min(int(h_score), 100),
        "good_to_buy_total": min(int(b_score), 100),
        "health_breakdown": h_breakdown,
        "buy_breakdown": b_breakdown
    }


def calculate_beneish_m_score(metrics):
    industry = (metrics.get('industry') or "").lower()
    sector = (metrics.get('sector') or "").lower()
    is_fin = 'financial' in sector
    is_reit = 'real estate' in sector or 'reit' in sector
    
    if is_fin or is_reit:
        return {"m_score": None, "label": "N/A (Not Applicable for Financials/REITs)", "status": "neutral"}
        
    beneish = metrics.get('beneish_data')
    if not beneish or not beneish.get('current') or not beneish.get('prev'):
        return {"m_score": None, "label": "N/A - Incomplete Data", "status": "neutral"}
        
    curr = beneish['current']
    prev = beneish['prev']
    
    # Fallback for Service/Tech companies with no explicitly reported "Gross Profit"
    if curr.get('gross_profit') is None and curr.get('sales') is not None:
        curr['gross_profit'] = curr['sales']
    if prev.get('gross_profit') is None and prev.get('sales') is not None:
        prev['gross_profit'] = prev['sales']
    
    def safe_div(n, d):
        if d is None or n is None or d == 0: return None
        return float(n) / float(d)
        
    try:
        # 1. DSRI = (Net Receivables_current / Sales_current) / (Net Receivables_prev / Sales_prev)
        dsri = safe_div(safe_div(curr['net_receivables'], curr['sales']), safe_div(prev['net_receivables'], prev['sales']))
        
        # 2. GMI = Gross Margin_prev / Gross Margin_current
        gmi = safe_div(safe_div(prev['gross_profit'], prev['sales']), safe_div(curr['gross_profit'], curr['sales']))
        
        # 3. AQI = [1 - (Current Assets_current + PP&E_current) / Total Assets_current] / [1 - (Current Assets_prev + PP&E_prev) / Total Assets_prev]
        def get_aqi_part(ca, ppe, ta):
            if ca is None or ppe is None or ta is None or ta == 0: return None
            return 1 - ((float(ca) + float(ppe)) / float(ta))
        aqi = safe_div(get_aqi_part(curr['current_assets'], curr['ppe'], curr['total_assets']), get_aqi_part(prev['current_assets'], prev['ppe'], prev['total_assets']))
        
        # 4. SGI = Sales_current / Sales_prev
        sgi = safe_div(curr['sales'], prev['sales'])
        
        # 5. DEPI = Depreciation Rate_prev / Depreciation Rate_current
        def get_dep_rate(dep, ppe):
            if dep is None or ppe is None or (float(dep) + float(ppe)) == 0: return None
            return float(dep) / (float(dep) + float(ppe))
        depi = safe_div(get_dep_rate(prev['depreciation'], prev['ppe']), get_dep_rate(curr['depreciation'], curr['ppe']))
        
        # 6. SGAI = (SGA_current / Sales_current) / (SGA_prev / Sales_prev)
        sgai = safe_div(safe_div(curr['sga'], curr['sales']), safe_div(prev['sga'], prev['sales']))
        
        # 7. LVGI = Leverage_current / Leverage_prev
        def get_leverage(cl, ltd, ta):
            if cl is None or ta is None or ta == 0: return None
            ltd_val = float(ltd) if ltd is not None else 0.0
            return (float(cl) + ltd_val) / float(ta)
        lvgi = safe_div(get_leverage(curr['current_liabilities'], curr['long_term_debt'], curr['total_assets']), get_leverage(prev['current_liabilities'], prev['long_term_debt'], prev['total_assets']))
        
        # 8. TATA = (Net Income_current - CFO_current) / Total Assets_current
        tata = None
        if curr['net_income_cont'] is not None and curr['cfo'] is not None and curr['total_assets'] and float(curr['total_assets']) > 0:
            tata = (float(curr['net_income_cont']) - float(curr['cfo'])) / float(curr['total_assets'])
            
        vars = [dsri, gmi, aqi, sgi, depi, sgai, lvgi, tata]
        if any(v is None for v in vars):
            return {"m_score": None, "label": "N/A - Incomplete Data", "status": "neutral"}
            
        m_score = -4.84 + (0.92 * dsri) + (0.528 * gmi) + (0.404 * aqi) + (0.892 * sgi) + (0.115 * depi) - (0.172 * sgai) + (4.679 * tata) - (0.327 * lvgi)
        
        breakdown = [
            {"metric": "DSRI (Days Sales in Receivables)", "value": round(dsri, 4), "threshold": "> 1.0 indicates inflated revenues", "status": "fail" if dsri > 1.2 else "pass"},
            {"metric": "GMI (Gross Margin Index)", "value": round(gmi, 4), "threshold": "> 1.0 indicates deteriorating margins", "status": "fail" if gmi > 1.1 else "pass"},
            {"metric": "AQI (Asset Quality Index)", "value": round(aqi, 4), "threshold": "> 1.0 indicates increased cost deferral", "status": "fail" if aqi > 1.1 else "pass"},
            {"metric": "SGI (Sales Growth Index)", "value": round(sgi, 4), "threshold": "> 1.0 means growing sales (can be an incentive to manipulate)", "status": "neutral"},
            {"metric": "DEPI (Depreciation Index)", "value": round(depi, 4), "threshold": "> 1.0 indicates assets depreciating slower", "status": "fail" if depi > 1.1 else "pass"},
            {"metric": "SGAI (Sales, General & Admin Index)", "value": round(sgai, 4), "threshold": "> 1.0 indicates decreasing administrative efficiency", "status": "fail" if sgai > 1.1 else "pass"},
            {"metric": "LVGI (Leverage Index)", "value": round(lvgi, 4), "threshold": "> 1.0 indicates increasing leverage", "status": "fail" if lvgi > 1.1 else "pass"},
            {"metric": "TATA (Total Accruals to Total Assets)", "value": round(tata, 4), "threshold": "Higher positive value indicates higher accruals (risk)", "status": "fail" if tata > 0.05 else "pass"}
        ]
        
        if m_score < -1.78:
            return {"m_score": round(m_score, 2), "label": "Pass: Low Risk of Manipulation", "status": "pass", "breakdown": breakdown}
        else:
            return {"m_score": round(m_score, 2), "label": "Fail: High Risk of Manipulation", "status": "fail", "breakdown": breakdown}
    except Exception as e:
        return {"m_score": None, "label": "N/A - Calculation Error", "status": "neutral"}

def calculate_health_score(metrics):
    res = calculate_scoring_reform({"margin_of_safety": 0}, metrics)
    b_score = calculate_beneish_m_score(metrics)
    tot = res["health_score_total"]
    breakdown = res["health_breakdown"]
    return {"total": tot, "breakdown": breakdown, "beneish": b_score}


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

    prof = metrics.get('company_profile', {})
    fwd_rev = safe_float(prof.get('forward_revenue'))
    ttm_rev = safe_float(prof.get('total_revenue') or metrics.get('revenue'))
    
    if fwd_rev > 0 and ttm_rev > 0:
        rev_growth_raw = (fwd_rev / ttm_rev) - 1.0
        rev_growth_label = "Fwd 1Y Revenue Growth"
        rev_growth_desc = "Estimates for the next 12 months."
    else:
        rev_growth_raw = safe_float(metrics.get('revenue_growth'))
        rev_growth_label = "Revenue Growth"
        rev_growth_desc = "Most recent historical 1-year revenue growth."

    rev_growth = rev_growth_raw * 100.0 if (0 < abs(rev_growth_raw) < 1.0) else rev_growth_raw
    
    fcf = safe_float(metrics.get('fcf'))
    rev = safe_float(metrics.get('revenue') or ttm_rev)
    fcf_margin = (fcf / rev * 100.0) if (fcf and rev and rev > 0) else 0.0
    
    total = rev_growth + fcf_margin
    
    return {
        "revenue_growth": round(rev_growth, 2),
        "fcf_margin": round(fcf_margin, 2),
        "total": round(total, 2),
        "passed": total >= 40,
        "label": "Strong" if total >= 40 else ("Healthy" if total >= 30 else "Weak"),
        "rev_growth_label": rev_growth_label,
        "rev_growth_desc": rev_growth_desc
    }

