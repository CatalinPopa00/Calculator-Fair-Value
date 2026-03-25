def apply_relative_score(vc, vs, weight, type="higher_is_better"):
    """
    Applies the mathematical rules for relative scoring.
    Returns: points, is_strength, is_risk
    """
    if vc is None or vs is None or vs == 0:
        return weight * 0.5, False, False # Neutral if data missing

    if type == "higher_is_better":
        if vc > vs * 1.10:
            return weight, True, False
        if vc < vs * 0.90:
            return 0, False, True
        return weight * 0.5, False, False
    
    elif type == "lower_is_better":
        if vc < vs * 0.90:
            return weight, True, False
        if vc > vs * 1.10:
            return 0, False, True
        return weight * 0.5, False, False

    return weight * 0.5, False, False

def calculate_health_score(metrics: dict, sector_avg: dict):
    """
    Calculates Company Health Score (0-100) using strict quantitative rules.
    """
    try:
        score = 0
        top_strengths = []
        risk_factors = []
        breakdown = []

        indicators = [
            ("Debt-to-Equity", "debt_to_equity", 20, "lower_is_better"),
            ("ROIC", "roic", 20, "higher_is_better"),
            ("Interest Coverage", "interest_coverage", 15, "higher_is_better"),
            ("Current Ratio", "current_ratio", 15, "higher_is_better"),
            ("EBIT Margin", "ebit_margin", 15, "higher_is_better"),
            ("FCF Trend", "historic_fcf_growth", 15, "higher_is_better")
        ]

        for name, key, weight, type_rule in indicators:
            vc = metrics.get(key)
            vs = sector_avg.get(key)
            pts, is_s, is_r = apply_relative_score(vc, vs, weight, type_rule)
            
            score += pts
            if is_s: top_strengths.append(name)
            if is_r: risk_factors.append(name)
            breakdown.append({"name": name, "vc": vc, "vs": vs, "pts": pts, "max": weight})

        # Red Flag: Health
        de = metrics.get('debt_to_equity', 0) or 0
        ic = metrics.get('interest_coverage', 100) or 100
        if de > 3.0 or ic < 1.5:
            if score > 40: score = 40
            reason = []
            if de > 3.0: reason.append(f"D/E Critical ({de:.2f})")
            if ic < 1.5: reason.append(f"IC Critical ({ic:.1f})")
            risk_factors.append(f"RED FLAG Health: {', '.join(reason)}")

        return {
            "total": int(score),
            "top_strengths": top_strengths,
            "risk_factors": risk_factors,
            "breakdown": breakdown
        }
    except Exception as e:
        print(f"Health Score Error: {e}")
        return {"total": 0, "top_strengths": [], "risk_factors": [f"Error: {str(e)}"], "breakdown": {}}

def calculate_buy_score(metrics: dict, valuation_data: dict, sector_avg: dict):
    """
    Calculates Good to Buy Score (0-100) using strict quantitative rules.
    """
    try:
        score = 0
        top_strengths = []
        risk_factors = []
        breakdown = []

        # 1. Margin of Safety (Absolute Rule)
        mos = valuation_data.get('margin_of_safety')
        weight_mos = 30
        pts_mos = 0
        is_s_mos, is_r_mos = False, False
        if mos is not None:
            if mos >= 20.0:
                pts_mos = 30; is_s_mos = True
            elif mos >= 0.0:
                pts_mos = 15
            else:
                pts_mos = 0; is_r_mos = True
        
        score += pts_mos
        if is_s_mos: top_strengths.append("Margin of Safety")
        if is_r_mos: risk_factors.append("Margin of Safety")
        breakdown.append({"name": "Margin of Safety", "vc": mos, "vs": "N/A (Absolute)", "pts": pts_mos, "max": 30})

        # Select P/E or P/S (Lower is Better)
        # Use whichever provides a better relative score, or just picking one based on sector
        # For simplicity and to follow the 15pt weight, we check relative for both if available
        # But the prompt says "sau", so we pick one. Standard: P/E, fallback P/S.
        pe_vc = metrics.get('forward_pe')
        pe_vs = sector_avg.get('forward_pe')
        ps_vc = metrics.get('fwd_ps')
        ps_vs = sector_avg.get('fwd_ps')
        
        val_name = "Fwd P/E" if pe_vc and pe_vs else "Fwd P/S"
        val_vc = pe_vc if pe_vc and pe_vs else ps_vc
        val_vs = pe_vs if pe_vc and pe_vs else ps_vs
        
        indicators = [
            ("PEG Ratio", "peg_ratio", 20, "lower_is_better"),
            ("FCF Yield", "fcf_yield", 15, "higher_is_better"),
            (val_name, None, 15, "lower_is_better"), # val_vc/val_vs used directly
            ("Next 3Y Rev Growth Est", "next_3y_rev_est", 20, "higher_is_better")
        ]

        for name, key, weight, type_rule in indicators:
            if name == val_name:
                vc, vs = val_vc, val_vs
            else:
                vc = metrics.get(key)
                vs = sector_avg.get(key)
            
            pts, is_s, is_r = apply_relative_score(vc, vs, weight, type_rule)
            score += pts
            if is_s: top_strengths.append(name)
            if is_r: risk_factors.append(name)
            breakdown.append({"name": name, "vc": vc, "vs": vs, "pts": pts, "max": weight})

        # Red Flag: Buy
        if mos is not None and mos < -20.0:
            if score > 40: score = 40
            risk_factors.append(f"RED FLAG Valuation: MoS is {mos:.1f}% (Overvalued)")

        return {
            "total": int(score),
            "top_strengths": top_strengths,
            "risk_factors": risk_factors,
            "breakdown": breakdown
        }
    except Exception as e:
        print(f"Buy Score Error: {e}")
        return {"total": 0, "top_strengths": [], "risk_factors": [f"Error: {str(e)}"], "breakdown": {}}
