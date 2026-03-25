def apply_relative_score(vc, vs, weight, type="higher_is_better"):
    """
    STRICT EXPERT RULEBOOK (RELATIV):
    - Punctaj Maxim (100%): Dacă Vc > Vs * 1.10 (higher) sau Vc < Vs * 0.90 (lower).
    - Punctaj Mediu (50%): Dacă Vc este între Vs * 0.90 și Vs * 1.10 inclusiv.
    - Punctaj Zero (0%): Dacă Vc < Vs * 0.90 (higher) sau Vc > Vs * 1.10 (lower).
    """
    if vc is None or vs is None or vs == 0:
        return weight * 0.5, False, False # Neutral if data missing

    if type == "higher_is_better":
        if vc > vs * 1.10:
            return weight, True, False
        if vc < vs * 0.90:
            return 0, False, True
        return weight * 0.5, False, False # In between
    
    else: # lower_is_better
        if vc < vs * 0.90:
            return weight, True, False
        if vc > vs * 1.10:
            return 0, False, True
        return weight * 0.5, False, False # In between

def calculate_health_score(metrics: dict, sector_avg: dict):
    """
    Calculates Company Health Score (0-100) using strict expert rules.
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
            
            # Format value string
            val_str = "N/A"
            if vc is not None:
                suffix = "%" if key in ["roic", "ebit_margin", "historic_fcf_growth"] else "x"
                val_str = f"{vc:.1f}{suffix}" if vs is None else f"{vc:.1f}{suffix} (vs {vs:.1f}{suffix} med.)"
            
            breakdown.append({
                "name": name, 
                "value": val_str,
                "pts": pts, 
                "max": weight
            })

        # --- RED FLAGS HEALTH ---
        de = metrics.get('debt_to_equity')
        ic = metrics.get('interest_coverage')
        has_flag = False
        if de is not None and de > 3.0:
            has_flag = True
            risk_factors.append("RED FLAG: Debt-to-Equity > 3.0")
        if ic is not None and ic < 1.5:
            has_flag = True
            risk_factors.append("RED FLAG: Interest Coverage < 1.5")
        
        if has_flag:
            score = min(score, 40)

        return {
            "total": round(score, 1),
            "top_strengths": top_strengths,
            "risk_factors": list(set(risk_factors)),
            "breakdown": breakdown
        }
    except Exception as e:
        print(f"Health Score Error: {e}")
        return {"total": 0, "top_strengths": [], "risk_factors": [str(e)], "breakdown": []}

def calculate_buy_score(metrics: dict, valuation_data: dict, sector_avg: dict):
    """
    Calculates Good to Buy Score (0-100) using strict expert rules.
    """
    try:
        score = 0
        top_strengths = []
        risk_factors = []
        breakdown = []

        # 1. Margin of Safety (REGULA ABSOLUTA)
        mos = valuation_data.get('margin_of_safety')
        pts_mos = 0
        if mos is not None:
            if mos >= 20.0:
                pts_mos = 30
                top_strengths.append("Margin of Safety")
            elif 0 <= mos < 20.0:
                pts_mos = 15
            else:
                pts_mos = 0
                risk_factors.append("Margin of Safety")
        
        score += pts_mos
        breakdown.append({
            "name": "Margin of Safety", 
            "value": f"{mos:.1f}%" if mos is not None else "N/A", 
            "pts": pts_mos, 
            "max": 30
        })

        # Select P/E or P/S (Lower is Better)
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
            (val_name, None, 15, "lower_is_better"), 
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
            
            val_str = "N/A"
            if vc is not None:
                suffix = "%" if "Growth" in name or "Yield" in name else "x"
                val_str = f"{vc:.1f}{suffix}" if vs is None else f"{vc:.1f}{suffix} (vs {vs:.1f}{suffix} med.)"

            breakdown.append({
                "name": name, 
                "value": val_str,
                "pts": pts, 
                "max": weight
            })

        # --- RED FLAGS BUY ---
        if mos is not None and mos < -20.0:
            score = min(score, 40)
            risk_factors.append("RED FLAG: Margin of Safety < -20% (Severely Overvalued)")

        return {
            "total": round(score, 1),
            "top_strengths": top_strengths,
            "risk_factors": list(set(risk_factors)),
            "breakdown": breakdown
        }
    except Exception as e:
        print(f"Buy Score Error: {e}")
        return {"total": 0, "top_strengths": [], "risk_factors": [str(e)], "breakdown": []}
