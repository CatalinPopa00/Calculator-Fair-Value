def calculate_peter_lynch(current_price: float, trailing_eps: float, eps_growth_estimated: float, pe_historic: float, sector_median_pe: float = 20.0, discount_rate: float = 0.09):
    """
    Refined Peter Lynch Model (Forward Multiple):
    1. FWD EPS (3Y) = trailing_eps * ((1 + eps_growth_estimated) ** 3)
    2. FWD PE = current_price / FWD EPS (3Y)
    3. Price Target (3Y) = FWD EPS * pe_historic
    4. Fair Value Today = Price Target / ((1 + discount_rate) ** 3)
    """
    if trailing_eps is None or trailing_eps <= 0 or eps_growth_estimated is None or current_price is None:
        return {"fwd_pe": None, "fair_value": None, "fair_value_pe_20": None, "fair_value_sector_pe": None, "status": "N/A"}
    
    # Use default 20 if historic is missing
    safe_pe_historic = pe_historic if pe_historic else 20.0
    safe_sector_pe = sector_median_pe if sector_median_pe else 20.0
    
    # FWD EPS in 3 years
    fwd_eps = trailing_eps * ((1 + eps_growth_estimated) ** 3)
    
    if fwd_eps == 0:
        return {"fwd_pe": None, "fair_value": None, "fair_value_pe_20": None, "fair_value_sector_pe": None, "status": "N/A"}
        
    fwd_pe = current_price / fwd_eps
    
    # Price Targets in 3 years
    pt_historic = fwd_eps * safe_pe_historic
    pt_pe_20 = fwd_eps * 20
    pt_sector_pe = fwd_eps * safe_sector_pe
    
    # DISCOUNT TO PRESENT VALUE (3 Years)
    discount_factor = (1 + discount_rate) ** 3
    fair_value = pt_historic / discount_factor
    fair_value_pe_20 = pt_pe_20 / discount_factor
    fair_value_sector_pe = pt_sector_pe / discount_factor
    
    status = "Overvalued" if fwd_pe > (safe_pe_historic * 0.8) else "Undervalued"
    
    return {
        "trailing_eps": trailing_eps,
        "eps_growth_estimated": eps_growth_estimated,
        "fwd_eps": fwd_eps,
        "fwd_pe": fwd_pe,
        "fair_value": fair_value,
        "fair_value_pe_20": fair_value_pe_20,
        "fair_value_sector_pe": fair_value_sector_pe,
        "status": status,
        "discount_rate_applied": discount_rate
    }

def calculate_peg_fair_value(current_price: float, company_peg: float, industry_peg: float):
    """
    User's requested formula:
    peg_fair_value = current_price * (industry_peg / company_peg)
    
    This applies only if company_peg > 0 and industry_peg > 0.
    """
    if not all([current_price, company_peg, industry_peg]):
        return None
        
    if company_peg <= 0 or industry_peg <= 0:
        return None
        
    return current_price * (industry_peg / company_peg)

def calculate_dcf(fcf: float, growth_rate: float, discount_rate: float, perpetual_growth: float, shares_outstanding: int, total_cash: float = 0, total_debt: float = 0, years: int = 5, buyback_rate: float = 0.0, exit_multiple: float = 15.0):
    """
    Discounted Cash Flow (DCF) - Dual Method.
    WACC Smart Cap: Forced between 7% and 10.5%.
    """
    if not all([fcf, shares_outstanding]):
        return None

    # 1. WACC Smart Cap
    wacc = max(0.07, min(discount_rate, 0.105))
    
    buyback_rate = float(buyback_rate or 0.0)
    current_fcf = fcf
    cash_flows = []
    pv_cash_flows_list = []

    # 2. Projections
    for i in range(1, years + 1):
        current_fcf *= (1 + growth_rate)
        cash_flows.append(current_fcf)
        pv = current_fcf / ((1 + wacc) ** i)
        pv_cash_flows_list.append(pv)

    sum_pv_cf = sum(pv_cash_flows_list)

    # Scenariul A: Perpetual Growth
    terminal_denom = (wacc - perpetual_growth)
    if abs(terminal_denom) < 0.0001: terminal_denom = 0.0001
    tv_perp = (cash_flows[-1] * (1 + perpetual_growth)) / terminal_denom
    pv_tv_perp = tv_perp / ((1 + wacc) ** years)

    # Scenariul B: Exit Multiple
    tv_exit = cash_flows[-1] * exit_multiple
    pv_tv_exit = tv_exit / ((1 + wacc) ** years)

    # Effective Shares (Buyback)
    effective_shares = shares_outstanding * ((1 - buyback_rate) ** years)
    if effective_shares <= 0: effective_shares = shares_outstanding

    def finalize_valuation(pv_tv):
        ev = sum_pv_cf + pv_tv
        equity = ev + (total_cash or 0) - (total_debt or 0)
        return {
            "enterprise_value": ev,
            "equity_value": equity,
            "fair_value": equity / effective_shares,
            "terminal_value": pv_tv * ((1 + wacc) ** years), # Original TV
            "pv_terminal_value": pv_tv
        }

    perp_res = finalize_valuation(pv_tv_perp)
    exit_res = finalize_valuation(pv_tv_exit)

    return {
        "discount_rate_applied": wacc,
        "fcf_years": cash_flows,
        "pv_fcf_years": pv_cash_flows_list,
        "total_pv_of_fcfs": sum_pv_cf,
        "dcf_perpetual": perp_res,
        "dcf_exit_multiple": exit_res,
        "effective_shares": effective_shares,
        "buyback_rate_applied": buyback_rate
    }
    
def calculate_dcf_sensitivity(fcf: float, growth_rate: float, shares_outstanding: int, total_cash: float = 0, total_debt: float = 0, years: int = 5, base_discount: float = 0.09, base_perp: float = 0.02, exit_multiple: float = 15.0):
    """
    Calculates a 3x3 matrix for Perpetual Growth scenario.
    """
    if not all([fcf, shares_outstanding]):
        return None
        
    discounts = [base_discount - 0.01, base_discount, base_discount + 0.01]
    perps = [base_perp - 0.005, base_perp, base_perp + 0.005]
    
    matrix = []
    for d in discounts:
        row = {"discount_rate": d, "values": []}
        for p in perps:
            res = calculate_dcf(fcf, growth_rate, d, p, shares_outstanding, total_cash, total_debt, years, exit_multiple=exit_multiple)
            val = res.get("dcf_perpetual", {}).get("fair_value") if res else None
            row["values"].append({"perpetual_growth": p, "fair_value": val})
        matrix.append(row)
    return matrix

def calculate_reverse_dcf(current_price: float, current_fcf: float, discount_rate: float, perpetual_growth: float, shares_outstanding: int, total_cash: float = 0, total_debt: float = 0, years: int = 5, exit_multiple: float = 15.0):
    """
    Finds implied growth for Perpetual Growth scenario.
    """
    if not all([current_price, current_fcf, shares_outstanding]):
        return None
        
    market_cap = current_price * shares_outstanding
    target_ev = market_cap - (total_cash or 0) + (total_debt or 0)
    
    if target_ev <= 0: return None
        
    low, high = -0.20, 0.50
    implied_growth = None
    
    for _ in range(30):
        mid = (low + high) / 2
        res = calculate_dcf(current_fcf, mid, discount_rate, perpetual_growth, shares_outstanding, total_cash, total_debt, years, exit_multiple=exit_multiple)
        if not res: return None
            
        calc_ev = res.get("dcf_perpetual", {}).get("enterprise_value")
        if not calc_ev: return None

        if abs(calc_ev - target_ev) / target_ev < 0.001:
            implied_growth = mid
            break
            
        if calc_ev > target_ev: high = mid
        else: low = mid
            
    return implied_growth if implied_growth is not None else (low + high) / 2
import statistics

def calculate_relative_valuation(company_ticker: str, company_metrics: dict, competitors_metrics: list):
    """
    Averages P/E, P/S, Margins, FCF of competitors. Now uses Median with P/S fallback.
    """
    if not competitors_metrics:
        return None
        
    # Phase 1: Try median P/E
    valid_pes = [p.get('pe_ratio') if isinstance(p, dict) else None for p in competitors_metrics]
    valid_pes = [v for v in valid_pes if v is not None and v > 0]
    
    company_eps = company_metrics.get('trailing_eps')
    if valid_pes and company_eps and company_eps > 0:
        median_pe = statistics.median(valid_pes)
        return median_pe * company_eps
        
    # Phase 2: Fallback to median P/S ratio if P/E fails
    valid_ps = [p.get('ps_ratio') if isinstance(p, dict) else None for p in competitors_metrics]
    valid_ps = [v for v in valid_ps if v is not None and v > 0]
    
    company_revenue_per_share = company_metrics.get('revenue_per_share')
    if valid_ps and company_revenue_per_share and company_revenue_per_share > 0:
        median_ps = statistics.median(valid_ps)
        return median_ps * company_revenue_per_share

    return None
