def calculate_health_score(metrics: dict):
    """
    Calculates the Company Health Score (0-100).
    Requires: debt_to_equity, fcf_history (list of last 3 years), current_ratio, roic, interest_coverage
    Returns dict {"total": int, "breakdown": list of dicts} or "N/A"
    """
    try:
        score = 0
        breakdown = []
        
        # Helper to add breakdown
        def add_brk(name, val, pts, max_pts):
            breakdown.append({
                "name": name,
                "value": val,
                "points": pts,
                "max_points": max_pts
            })

        # 1. Debt-to-Equity (Max 20)
        de = metrics.get('debt_to_equity')
        pts = 0
        de_str = "N/A"
        if de is not None:
            de_str = f"{de:.2f}x"
            if de < 0.5:
                pts = 20
            elif 0.5 <= de <= 1.0:
                pts = 15
            elif 1.0 < de <= 2.0:
                pts = 5
            # > 2.0 is 0
        score += pts
        add_brk("Debt-to-Equity (Solvency)", de_str, pts, 20)
            
        # 2. FCF Trend (Max 20)
        fcf_hist = metrics.get('fcf_history')
        pts = 0
        trend_str = "N/A"
        if fcf_hist and len(fcf_hist) >= 2: 
            recent_fcf = fcf_hist[0]
            if recent_fcf < 0:
                pts = 0
                trend_str = "Negative"
            elif len(fcf_hist) >= 3:
                y1, y2, y3 = fcf_hist[0], fcf_hist[1], fcf_hist[2]
                if y1 > 0 and y2 > 0 and y3 > 0:
                    if y1 > y2 and y2 > y3:
                        pts = 20
                        trend_str = "3 Yrs Growth"
                    else:
                        pts = 10
                        trend_str = "3 Yrs Fluctuating"
                else:
                    if y2 > 0 or y3 > 0:
                        pts = 5
                        trend_str = "2/3 Yrs Positive"
                    else:
                        trend_str = "1/3 Yrs Positive"
            elif len(fcf_hist) == 2:
                y1, y2 = fcf_hist[0], fcf_hist[1]
                if y1 > 0 and y2 > 0:
                    if y1 > y2: 
                        pts = 20
                        trend_str = "2 Yrs Growth"
                    else: 
                        pts = 10
                        trend_str = "2 Yrs Fluctuating"
                elif y1 > 0:
                    pts = 5
                    trend_str = "1/2 Yrs Positive"
        elif fcf_hist and len(fcf_hist) == 1:
            if fcf_hist[0] > 0:
                pts = 5
                trend_str = "1 Yr Positive"
            else:
                pts = 0
                trend_str = "Negative"
                
        score += pts
        add_brk("FCF Trend (Quality)", trend_str, pts, 20)

        # 3. EBIT Margin (Max 15)
        ebit_m = metrics.get('ebit_margin')
        pts = 0
        ebit_m_str = "N/A"
        if ebit_m is not None:
            ebit_m_str = f"{ebit_m * 100:.1f}%"
            if ebit_m > 0.15:
                pts = 15
            elif 0.08 <= ebit_m <= 0.15:
                pts = 10
            # < 0.08 is 0
        score += pts
        add_brk("EBIT Margin (Profitability)", ebit_m_str, pts, 15)

        # 4. Current Ratio (Max 15)
        cr = metrics.get('current_ratio')
        pts = 0
        cr_str = "N/A"
        if cr is not None:
            cr_str = f"{cr:.2f}x"
            if cr > 1.5:
                pts = 15
            elif 1.0 <= cr <= 1.5:
                pts = 10
            # < 1.0 is 0
        score += pts
        add_brk("Current Ratio (Liquidity)", cr_str, pts, 15)
            
        # 5. ROIC (Max 15)
        roic = metrics.get('roic')
        pts = 0
        roic_str = "N/A"
        if roic is not None:
            roic_str = f"{roic * 100:.1f}%"
            if roic > 0.15:
                pts = 15
            elif 0.10 <= roic <= 0.15:
                pts = 10
            elif 0.05 <= roic < 0.10:
                pts = 5
        score += pts
        add_brk("ROIC (Efficiency)", roic_str, pts, 15)
            
        # 6. Interest Coverage (Max 15)
        ic = metrics.get('interest_coverage')
        pts = 0
        ic_str = "N/A"
        if ic is None: 
            if metrics.get('total_debt', 0) == 0:
                pts = 15
                ic_str = "No Debt"
        else:
            ic_str = f"{ic:.1f}x"
            if ic > 5.0:
                pts = 15
            elif 3.0 <= ic <= 5.0:
                pts = 10
            # < 3.0 is 0
        score += pts
        add_brk("Interest Coverage (Safety)", ic_str, pts, 15)
                
        return {"total": score, "breakdown": breakdown}
    except Exception as e:
        print(f"Health Score Error: {e}")
        return "N/A"


def calculate_buy_score(valuation_data: dict, metrics: dict):
    """
    Calculates the Good to Buy Score (0-100).
    Requires margin_of_safety (decimal or %), peg_ratio, fcf_yield, eps_growth
    Returns dict {"total": int, "breakdown": list of dicts} or "N/A"
    """
    try:
        score = 0
        breakdown = []
        
        def add_brk(name, val, pts, max_pts):
            breakdown.append({
                "name": name,
                "value": val,
                "points": pts,
                "max_points": max_pts
            })
            
        # 1. Margin of Safety (Max 30)
        mos = valuation_data.get('margin_of_safety')
        pts = 0
        mos_str = "N/A"
        if mos is not None:
            mos_str = f"{mos:.1f}%"
            if mos > 30.0:
                pts = 30
            elif 15.0 <= mos <= 30.0:
                pts = 20
            elif 0.0 <= mos < 15.0:
                pts = 10
            # < 0 is 0
        score += pts
        add_brk("Margin of Safety (Value)", mos_str, pts, 30)
        
        # 2. PEG Ratio (Max 20)
        peg = metrics.get('peg_ratio')
        pts = 0
        peg_str = "N/A"
        if peg is not None and peg > 0:
            peg_str = f"{peg:.2f}x"
            if peg < 1.0:
                pts = 20
            elif 1.0 <= peg <= 1.5:
                pts = 10
            elif 1.5 < peg <= 2.0:
                pts = 5
            # > 2.0 is 0
        score += pts
        add_brk("PEG Ratio (Growth Value)", peg_str, pts, 20)

        # 3. FWD P/S (Max 15)
        fwd_ps = metrics.get('fwd_ps')
        pts = 0
        fwd_ps_str = "N/A"
        if fwd_ps is not None:
            fwd_ps_str = f"{fwd_ps:.2f}x"
            if fwd_ps < 2.0:
                pts = 15
            elif 2.0 <= fwd_ps <= 5.0:
                pts = 10
            # > 5.0 is 0
        score += pts
        add_brk("FWD P/S (Revenue Value)", fwd_ps_str, pts, 15)
            
        # 4. FCF Yield (Max 15)
        fcf = metrics.get('fcf')
        mcap = metrics.get('market_cap')
        pts = 0
        fcf_yield_str = "N/A"
        
        if fcf is not None and mcap is not None and mcap > 0:
            fcf_yield = fcf / mcap
            fcf_yield_str = f"{fcf_yield * 100:.1f}%"
            if fcf_yield > 0.07:
                pts = 15
            elif 0.04 <= fcf_yield <= 0.07:
                pts = 10
            # < 0.04 is 0
        score += pts
        add_brk("FCF Yield (Cash Return)", fcf_yield_str, pts, 15)

        # 5. Next 3Y Rev Est (Max 10)
        rev_est = metrics.get('next_3y_rev_est')
        pts = 0
        rev_est_str = "N/A"
        if rev_est is not None:
            rev_est_str = f"{rev_est * 100:.1f}%"
            if rev_est > 0.10:
                pts = 10
            elif 0.05 <= rev_est <= 0.10:
                pts = 5
            # < 0.05 is 0
        score += pts
        add_brk("Next 3Y Rev Est (Growth)", rev_est_str, pts, 10)
            
        # 6. 3-Year FWD EPS Growth (Max 10)
        eps_g = metrics.get('eps_growth')
        pts = 0
        eps_g_str = "N/A"
        if eps_g is not None:
            eps_g_str = f"{eps_g * 100:.1f}%"
            if eps_g > 0.15:
                pts = 10
            elif 0.05 <= eps_g <= 0.15:
                pts = 5
            # < 0.05 is 0
        score += pts
        add_brk("3-Yr FWD EPS Growth (Momentum)", eps_g_str, pts, 10)
            
        return {"total": score, "breakdown": breakdown}
    except Exception as e:
        print(f"Buy Score Error: {e}")
        return "N/A"
