def calculate_peter_lynch(current_price: float, trailing_eps: float, eps_growth: float, pe_historic: float):
    """
    User's exact requested formula:
    1. FWD EPS = EPS_curent * (1+estimated earnings growth for next year)^3
    2. FWD PE = Pret curent / FWD EPS
    
    If FWD PE > 20 -> Overvalued
    
    Fair Value = FWD EPS * PE istoric al companiei
    """
    if trailing_eps is None or trailing_eps <= 0 or eps_growth is None or current_price is None or pe_historic is None:
        return {"fwd_pe": None, "fair_value": None, "status": "N/A"}
    
    fwd_eps = trailing_eps * ((1 + eps_growth) ** 3)
    
    if fwd_eps == 0:
        return {"fwd_pe": None, "fair_value": None, "status": "N/A"}
        
    fwd_pe = current_price / fwd_eps
    fair_value = fwd_eps * pe_historic
    status = "Overvalued" if fwd_pe > 20 else "Undervalued"
    
    # PE=20 scenario
    fair_value_pe_20 = fwd_eps * 20
    
    return {
        "fwd_pe": fwd_pe, 
        "fwd_eps": fwd_eps,
        "fair_value": fair_value, 
        "fair_value_pe_20": fair_value_pe_20,
        "status": status
    }

def calculate_peg_fair_value(eps: float, growth_rate: float):
    """
    If Target PEG is 1.0, then Target P/E = Growth Rate.
    Fair Value = EPS * Target P/E = EPS * (Growth Rate * 100).
    """
    if eps is None or eps <= 0 or growth_rate is None or growth_rate <= 0:
        return None
        
    return eps * (growth_rate * 100)

def calculate_dcf(fcf: float, growth_rate: float, discount_rate: float, perpetual_growth: float, shares_outstanding: int, total_cash: float = 0, total_debt: float = 0, years: int = 5, buyback_rate: float = 0.0):
    """
    Discounted Cash Flow (DCF). Returns granular dictionary.
    buyback_rate: annual share reduction rate (e.g. 0.03 = 3%/yr buyback).
      After `years` years, effective shares = shares * (1 - buyback_rate)^years.
      This increases per-share intrinsic value proportionally.
    """
    if not all([fcf, shares_outstanding]):
        return None

    buyback_rate = float(buyback_rate or 0.0)

    cash_flows = []
    pv_cash_flows_list = []
    current_fcf = fcf
    for i in range(1, years + 1):
        current_fcf *= (1 + growth_rate)
        cash_flows.append(current_fcf)
        pv = current_fcf / ((1 + discount_rate) ** i)
        pv_cash_flows_list.append(pv)

    # Discount Cash Flows Additive
    sum_pv_cf = sum(pv_cash_flows_list)

    # Terminal Value
    terminal_denom = (discount_rate - perpetual_growth)
    if abs(terminal_denom) < 0.0001:
        terminal_denom = 0.0001
        
    terminal_value = (cash_flows[-1] * (1 + perpetual_growth)) / terminal_denom
    pv_terminal_value = terminal_value / ((1 + discount_rate) ** years)

    total_enterprise_value = sum_pv_cf + pv_terminal_value

    # Bridge to Equity Value
    safe_cash = total_cash if total_cash is not None else 0
    safe_debt = total_debt if total_debt is not None else 0
    equity_value = total_enterprise_value + safe_cash - safe_debt

    # Apply share buyback: shares shrink each year, boosting per-share value
    effective_shares = shares_outstanding * ((1 - buyback_rate) ** years)
    if effective_shares <= 0:
        effective_shares = shares_outstanding

    implied_value_per_share = equity_value / effective_shares

    return {
        "fair_value": implied_value_per_share,
        "fcf_years": cash_flows,
        "pv_fcf_years": pv_cash_flows_list,
        "terminal_value": terminal_value,
        "pv_terminal_value": pv_terminal_value,
        "sum_pv_cf": sum_pv_cf,
        "enterprise_value": total_enterprise_value,
        "total_cash": safe_cash,
        "total_debt": safe_debt,
        "equity_value": equity_value,
        "effective_shares": effective_shares,
        "buyback_rate_applied": buyback_rate
    }
    
def calculate_dcf_sensitivity(fcf: float, growth_rate: float, shares_outstanding: int, total_cash: float = 0, total_debt: float = 0, years: int = 5, base_discount: float = 0.09, base_perp: float = 0.02):
    """
    Calculates a 3x3 matrix of DCF fair values for +/- 1% WACC and +/- 0.5% Perpetual Growth.
    """
    if not all([fcf, shares_outstanding]):
        return None
        
    discounts = [base_discount - 0.01, base_discount, base_discount + 0.01]
    perps = [base_perp - 0.005, base_perp, base_perp + 0.005]
    
    matrix = []
    
    for d in discounts:
        row = {"discount_rate": d, "values": []}
        for p in perps:
            res = calculate_dcf(fcf, growth_rate, d, p, shares_outstanding, total_cash, total_debt, years)
            val = res.get("fair_value") if res else None
            row["values"].append({"perpetual_growth": p, "fair_value": val})
        matrix.append(row)
        
    return matrix

def calculate_reverse_dcf(current_price: float, current_fcf: float, discount_rate: float, perpetual_growth: float, shares_outstanding: int, total_cash: float = 0, total_debt: float = 0, years: int = 5):
    """
    Finds the implied growth rate that makes the Calculated EV equal to the Target EV.
    Target EV = (Current Price * Shares Outstanding) - Cash + Debt
    Uses binary search algorithm.
    """
    if not all([current_price, current_fcf, shares_outstanding]):
        return None
        
    market_cap = current_price * shares_outstanding
    # Target EV = Market Cap - Cash + Total Debt (per user's equation)
    target_ev = market_cap - total_cash + total_debt
    
    if target_ev <= 0:
        return None
        
    low = -0.20 # -20% growth bounds
    high = 0.50 # +50% growth bounds
    
    implied_growth = None
    
    for _ in range(50):
        mid = (low + high) / 2
        res = calculate_dcf(current_fcf, mid, discount_rate, perpetual_growth, shares_outstanding, total_cash, total_debt, years)
        if not res or res.get("enterprise_value") is None:
            return None
            
        calc_ev = res.get("enterprise_value")
        
        # Check margin of error < 0.1%
        if abs(calc_ev - target_ev) / target_ev < 0.001:
            implied_growth = mid
            break
            
        if calc_ev > target_ev:
            high = mid
        else:
            low = mid
            
    return implied_growth if implied_growth is not None else (low + high) / 2
import statistics

def calculate_relative_valuation(company_ticker: str, company_metrics: dict, competitors_metrics: list):
    """
    Averages P/E, P/S, Margins, FCF of competitors. Now uses Median.
    """
    if not competitors_metrics:
        return None
        
    # A simple relative value based on median P/E of peers
    valid_pes = [p.get('pe_ratio') if isinstance(p, dict) else None for p in competitors_metrics]
    valid_pes = [v for v in valid_pes if v is not None]
    if not valid_pes:
        return None
        
    median_pe = statistics.median(valid_pes)
    
    company_eps = company_metrics.get('trailing_eps')
    if company_eps and company_eps > 0:
        return median_pe * company_eps
        
    return None
