def calculate_health_score(metrics: dict):
    """
    Calculates the Company Health Score (0-100) using Sector-Specific Architecture.
    """
    try:
        score = 0
        breakdown = []
        sector = metrics.get('sector', '')
        
        def add_brk(name, val, pts, max_pts):
            breakdown.append({
                "name": name,
                "value": val if val is not None else "N/A",
                "points": int(pts),
                "max_points": int(max_pts)
            })

        def get_fcf_trend(fcf_hist):
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
                            pts = 20; trend_str = "3 Yrs Growth"
                        else:
                            pts = 10; trend_str = "3 Yrs Fluctuating"
                    else:
                        pts = 5; trend_str = "2/3 Yrs Positive"
                elif len(fcf_hist) == 2:
                    y1, y2 = fcf_hist[0], fcf_hist[1]
                    if y1 > 0 and y2 > 0:
                        pts = 20 if y1 > y2 else 10
                        trend_str = "2 Yrs Growth" if y1 > y2 else "2 Yrs Fluctuating"
                    elif y1 > 0:
                        pts = 5; trend_str = "1/2 Yrs Positive"
            elif fcf_hist and len(fcf_hist) == 1:
                pts = 5 if fcf_hist[0] > 0 else 0
                trend_str = "1 Yr Positive" if fcf_hist[0] > 0 else "Negative"
            return pts, trend_str

        # 1. Financial Services (Bank/Fintech Model)
        if sector == "Financial Services":
            # P/B (Valuation replacement for D/E)
            pb = metrics.get('price_to_book')
            pts = 0; pb_s = "N/A"
            if pb is not None:
                pb_s = f"{pb:.2f}x"
                if pb < 1.5: pts = 20
                elif pb < 2.5: pts = 10
            else: # Neutral if missing
                pts = 20; pb_s = "Sector Neutral"
            score += pts
            add_brk("Price-to-Book (Valuation)", pb_s, pts, 20)

            # FCF Trend (Neutralized - Max Points for Financials)
            score += 20
            add_brk("FCF Trend (Quality)", "Sector Neutral", 20, 20)

            # ROE (Replacement for EBIT Margin)
            roe = metrics.get('roe')
            pts = 0; roe_s = "N/A"
            if roe is not None:
                roe_s = f"{roe * 100:.1f}%"
                if roe > 0.08: pts = 15
                elif roe > 0.04: pts = 10
            else: # Neutral if missing
                pts = 15; roe_s = "Sector Neutral"
            score += pts
            add_brk("ROE (Profitability)", roe_s, pts, 15)

            # Current Ratio (Neutralized)
            score += 15
            add_brk("Current Ratio (Liquidity)", "Sector Exempt", 15, 15)

            # ROA (Replacement for ROIC)
            roa = metrics.get('roa')
            pts = 0; roa_s = "N/A"
            if roa is not None:
                roa_s = f"{roa * 100:.1f}%"
                if roa > 0.008: pts = 15
                elif roa > 0.004: pts = 10
            else: # Neutral if missing
                pts = 15; roa_s = "Sector Neutral"
            score += pts
            add_brk("ROA (Efficiency)", roa_s, pts, 15)

            # Interest Coverage (Sector Exempt)
            score += 15
            add_brk("Interest Coverage (Safety)", "Sector Exempt", 15, 15)

        # 2. Real Estate (REIT Model)
        elif sector == "Real Estate":
            # D/E Relaxed
            de = metrics.get('debt_to_equity')
            pts = 0; de_s = "N/A"
            if de is not None:
                de_s = f"{de:.2f}x"
                if de < 2.0: pts = 20
                elif de < 3.0: pts = 10
            score += pts
            add_brk("Debt-to-Equity (Solvency)", de_s, pts, 20)

            # Operating Cash Flow replacement for FCF Trend
            ocf = metrics.get('operating_cashflow')
            pts = 0; ocf_s = "N/A"
            if ocf is not None:
                ocf_s = "Positive" if ocf > 0 else "Negative"
                pts = 20 if ocf > 0 else 0
            score += pts
            add_brk("Operating Cash Flow (Quality)", ocf_s, pts, 20)

            # EBIT Margin > 40%
            ebit_m = metrics.get('ebit_margin')
            pts = 0; em_s = "N/A"
            if ebit_m is not None:
                em_s = f"{ebit_m * 100:.1f}%"
                if ebit_m > 0.40: pts = 15
                elif ebit_m > 0.25: pts = 10
            score += pts
            add_brk("EBIT Margin (Profitability)", em_s, pts, 15)

            # Current Ratio
            cr = metrics.get('current_ratio')
            pts = 0; cr_s = "N/A"
            if cr is not None:
                cr_s = f"{cr:.2f}x"
                if cr >= 1.0: pts = 15
                elif cr >= 0.8: pts = 10
            score += pts
            add_brk("Current Ratio (Liquidity)", cr_s, pts, 15)

            # ROIC
            roic = metrics.get('roic')
            pts = 0; ric_s = "N/A"
            if roic is not None:
                ric_s = f"{roic * 100:.1f}%"
                if roic > 0.10: pts = 15
                elif roic > 0.05: pts = 10
            score += pts
            add_brk("ROIC (Efficiency)", ric_s, pts, 15)

            # Interest Coverage
            ic = metrics.get('interest_coverage')
            pts = 0; ic_s = "N/A"
            if ic is not None:
                ic_s = f"{ic:.1f}x"
                if ic > 3.0: pts = 15
                elif ic >= 2.0: pts = 10
            elif metrics.get('total_debt', 0) == 0:
                pts = 15; ic_s = "No Debt"
            score += pts
            add_brk("Interest Coverage (Safety)", ic_s, pts, 15)

        # 3. Utilities & Energy
        elif sector in ["Utilities", "Energy"]:
            # D/E Relaxed < 1.5
            de = metrics.get('debt_to_equity')
            pts = 0; de_s = "N/A"
            if de is not None:
                de_s = f"{de:.2f}x"
                if de < 1.5: pts = 20
                elif de < 2.5: pts = 10
            score += pts
            add_brk("Debt-to-Equity (Solvency)", de_s, pts, 20)

            # FCF Trend Neutral
            score += 10
            add_brk("FCF Trend (Quality)", "Sector Neutral (CapEx)", 10, 20)

            # EBIT Margin
            ebit_m = metrics.get('ebit_margin')
            pts = 0; em_s = "N/A"
            if ebit_m is not None:
                em_s = f"{ebit_m * 100:.1f}%"
                if ebit_m > 0.15: pts = 15
                elif ebit_m > 0.08: pts = 10
            score += pts
            add_brk("EBIT Margin (Profitability)", em_s, pts, 15)

            # Current Ratio Relaxed > 0.8
            cr = metrics.get('current_ratio')
            pts = 0; cr_s = "N/A"
            if cr is not None:
                cr_s = f"{cr:.2f}x"
                if cr > 0.8: pts = 15
                elif cr >= 0.6: pts = 10
            score += pts
            add_brk("Current Ratio (Liquidity)", cr_s, pts, 15)

            # ROIC
            roic = metrics.get('roic')
            pts = 0; ric_s = "N/A"
            if roic is not None:
                ric_s = f"{roic * 100:.1f}%"
                if roic > 0.10: pts = 15
                elif roic > 0.05: pts = 10
            score += pts
            add_brk("ROIC (Efficiency)", ric_s, pts, 15)

            # Interest Coverage
            ic = metrics.get('interest_coverage')
            pts = 0; ic_s = "N/A"
            if ic is not None:
                ic_s = f"{ic:.1f}x"
                if ic > 3.0: pts = 15
                elif ic >= 2.0: pts = 10
            elif metrics.get('total_debt', 0) == 0:
                pts = 15; ic_s = "No Debt"
            score += pts
            add_brk("Interest Coverage (Safety)", ic_s, pts, 15)

        # 4. Consumer Defensive
        elif sector == "Consumer Defensive":
            # Standard D/E
            de = metrics.get('debt_to_equity')
            pts = 0; de_s = "N/A"
            if de is not None:
                de_s = f"{de:.2f}x"
                if de < 0.5: pts = 20
                elif de < 1.0: pts = 15
            score += pts
            add_brk("Debt-to-Equity (Solvency)", de_s, pts, 20)

            # FCF Trend Standard
            pts, t_s = get_fcf_trend(metrics.get('fcf_history'))
            score += pts
            add_brk("FCF Trend (Quality)", t_s, pts, 20)

            # EBIT Margin > 6%
            ebit_m = metrics.get('ebit_margin')
            pts = 0; em_s = "N/A"
            if ebit_m is not None:
                em_s = f"{ebit_m * 100:.1f}%"
                if ebit_m > 0.06: pts = 15
                elif ebit_m > 0.03: pts = 10
            score += pts
            add_brk("EBIT Margin (Profitability)", em_s, pts, 15)

            # Current Ratio Standard
            cr = metrics.get('current_ratio')
            pts = 0; cr_s = "N/A"
            if cr is not None:
                cr_s = f"{cr:.2f}x"
                if cr > 1.5: pts = 15
                elif cr > 1.0: pts = 10
            score += pts
            add_brk("Current Ratio (Liquidity)", cr_s, pts, 15)

            # ROIC > 10%
            roic = metrics.get('roic')
            pts = 0; ric_s = "N/A"
            if roic is not None:
                ric_s = f"{roic * 100:.1f}%"
                if roic > 0.10: pts = 15
                elif roic > 0.06: pts = 10
            score += pts
            add_brk("ROIC (Efficiency)", ric_s, pts, 15)

            # Interest Coverage Standard
            ic = metrics.get('interest_coverage')
            pts = 0; ic_s = "N/A"
            if ic is not None:
                ic_s = f"{ic:.1f}x"
                if ic > 5.0: pts = 15
                elif ic >= 3.0: pts = 10
            elif metrics.get('total_debt', 0) == 0:
                pts = 15; ic_s = "No Debt"
            score += pts
            add_brk("Interest Coverage (Safety)", ic_s, pts, 15)

        # 5. Default (Technology, Healthcare, etc.) - Strict Pure Model
        else:
            # Debt-to-Equity (Strict)
            de = metrics.get('debt_to_equity')
            pts = 0; de_s = "N/A"
            if de is not None:
                de_s = f"{de:.2f}x"
                if de < 0.5: pts = 20
                elif de <= 1.0: pts = 15
                elif de <= 2.0: pts = 5
            score += pts
            add_brk("Debt-to-Equity (Solvency)", de_s, pts, 20)

            # FCF Trend (Strict)
            pts, t_s = get_fcf_trend(metrics.get('fcf_history'))
            score += pts
            add_brk("FCF Trend (Quality)", t_s, pts, 20)

            # EBIT Margin (Strict)
            ebit_m = metrics.get('ebit_margin')
            pts = 0; em_s = "N/A"
            if ebit_m is not None:
                em_s = f"{ebit_m * 100:.1f}%"
                if ebit_m > 0.15: pts = 15
                elif ebit_m >= 0.08: pts = 10
            score += pts
            add_brk("EBIT Margin (Profitability)", em_s, pts, 15)

            # Current Ratio (Strict)
            cr = metrics.get('current_ratio')
            pts = 0; cr_s = "N/A"
            if cr is not None:
                cr_s = f"{cr:.2f}x"
                if cr > 1.5: pts = 15
                elif cr >= 1.0: pts = 10
            score += pts
            add_brk("Current Ratio (Liquidity)", cr_s, pts, 15)

            # ROIC (Strict)
            roic = metrics.get('roic')
            pts = 0; ric_s = "N/A"
            if roic is not None:
                ric_s = f"{roic * 100:.1f}%"
                if roic > 0.15: pts = 15
                elif roic >= 0.10: pts = 10
                elif roic >= 0.05: pts = 5
            score += pts
            add_brk("ROIC (Efficiency)", ric_s, pts, 15)

            # Interest Coverage (Strict)
            ic = metrics.get('interest_coverage')
            pts = 0; ic_s = "N/A"
            if ic is not None:
                ic_s = f"{ic:.1f}x"
                if ic > 5.0: pts = 15
                elif ic >= 3.0: pts = 10
            elif metrics.get('total_debt', 0) == 0:
                pts = 15; ic_s = "No Debt"
            score += pts
            add_brk("Interest Coverage (Safety)", ic_s, pts, 15)

        return {"total": int(score), "breakdown": breakdown}
    except Exception as e:
        print(f"Health Score Error: {e}")
        return "N/A"


def calculate_buy_score(valuation_data: dict, metrics: dict):
    """
    Calculates the Good to Buy Score (0-100) using Sector-Specific Architecture.
    """
    try:
        score = 0
        breakdown = []
        sector = metrics.get('sector', '')
        
        def add_brk(name, val, pts, max_pts):
            breakdown.append({
                "name": name,
                "value": val if val is not None else "N/A",
                "points": int(pts),
                "max_points": int(max_pts)
            })
            
        # 1. Margin of Safety (Max 30) - UNCHANGED (Valuation Core)
        mos = valuation_data.get('margin_of_safety')
        pts = 0; mos_s = "N/A"
        if mos is not None:
            mos_s = f"{mos:.1f}%"
            if mos > 30.0: pts = 30
            elif mos >= 15.0: pts = 20
            elif mos >= 0.0: pts = 10
        score += pts
        add_brk("Margin of Safety (Value)", mos_s, pts, 30)
        
        # 2. PEG Ratio (Max 20)
        peg = metrics.get('peg_ratio')
        pts = 0; peg_s = "N/A"
        if peg is not None and peg > 0:
            peg_s = f"{peg:.2f}x"
            # More generous PEG for Financials/Stable sectors
            if sector == "Financial Services":
                if peg < 1.2: pts = 20
                elif peg <= 1.8: pts = 10
            else:
                if peg < 1.0: pts = 20
                elif peg <= 1.5: pts = 10
                elif peg <= 2.0: pts = 5
        score += pts
        add_brk("PEG Ratio (Growth Value)", peg_s, pts, 20)

        # 3. FWD P/S (Max 15)
        fwd_ps = metrics.get('fwd_ps')
        rev_est = metrics.get('next_3y_rev_est', 0) or 0
        pts = 0; ps_s = "N/A"
        
        if sector == "Financial Services":
            score += 15
            add_brk("FWD P/S (Revenue Value)", "Sector Exempt", 15, 15)
        elif fwd_ps is not None:
            ps_s = f"{fwd_ps:.2f}x"
            if fwd_ps < 2.0: pts = 15
            elif fwd_ps <= 5.0: pts = 10
            elif rev_est > 0.15: 
                # "Growth Forgiveness": If revenue growth > 15%, give partial points for high P/S
                pts = 7
                ps_s += " (Growth Premium)"
            score += pts
            add_brk("FWD P/S (Revenue Value)", ps_s, pts, 15)
        else:
            add_brk("FWD P/S (Revenue Value)", ps_s, 0, 15)
            
        # 4. Cash Return (Yield) (Max 15)
        # Replaces FCF Yield with Dividend Yield for certain sectors
        div_yield = metrics.get('dividend_yield') # Typically in % (e.g. 4.5 for 4.5%)
        # Normalization: ensure it's in %
        dy_val = div_yield if (div_yield and div_yield > 0.20) else (div_yield * 100 if div_yield else 0)
        
        if sector in ["Financial Services", "Real Estate"]:
            pts = 0; dy_s = "N/A"
            if div_yield and div_yield > 0:
                dy_val = div_yield * 100
                dy_s = f"{dy_val:.1f}%"
                if dy_val > 4.0: pts = 15
                elif dy_val > 2.5: pts = 10
            elif sector == "Financial Services":
                # Growth Fintechs often don't have dividends yet; don't penalize
                pts = 15; dy_s = "Neutral (Growth)"
                
            score += pts
            add_brk("Dividend Yield (Cash Return)", dy_s, pts, 15)
            
        elif sector in ["Utilities", "Energy"]:
            # Neutralize FCF Yield penalty for CapEx heavy sectors (min 50% pts)
            fcf = metrics.get('fcf'); mcap = metrics.get('market_cap')
            pts = 7; fcf_y_s = "Sector Neutral"
            if fcf and mcap and mcap > 0:
                y = (fcf / mcap) * 100
                fcf_y_s = f"{y:.1f}%"
                if y > 5.0: pts = 15
                elif y > 2.0: pts = 10
            score += pts
            add_brk("FCF Yield (Cash Return)", fcf_y_s, pts, 15)
            
        else: # Default FCF Yield
            fcf = metrics.get('fcf'); mcap = metrics.get('market_cap')
            pts = 0; fcf_y_s = "N/A"
            if fcf and mcap and mcap > 0:
                y = (fcf / mcap) * 100
                fcf_y_s = f"{y:.1f}%"
                if y > 7.0: pts = 15
                elif y > 4.0: pts = 10
            score += pts
            add_brk("FCF Yield (Cash Return)", fcf_y_s, pts, 15)

        # 5. Next 3Y Rev Est (Max 10)
        rev_est_m = metrics.get('next_3y_rev_est')
        pts = 0; re_s = "N/A"
        if rev_est_m is not None:
            re_s = f"{rev_est_m * 100:.1f}%"
            if rev_est_m > 0.10: pts = 10
            elif rev_est_m >= 0.05: pts = 5
        score += pts
        add_brk("Next 3Y Rev Est (Growth)", re_s, pts, 10)
            
        # 6. 3-Year FWD EPS Growth (Max 10)
        eps_g = metrics.get('eps_growth')
        pts = 0; eg_s = "N/A"
        if eps_g is not None:
            eg_s = f"{eps_g * 100:.1f}%"
            if eps_g > 0.15: pts = 10
            elif eps_g >= 0.05: pts = 5
        score += pts
        add_brk("3-Yr FWD EPS Growth (Momentum)", eg_s, pts, 10)
            
        return {"total": int(score), "breakdown": breakdown}
    except Exception as e:
        print(f"Buy Score Error: {e}")
        return "N/A"
