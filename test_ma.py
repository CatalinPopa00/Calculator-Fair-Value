"""
Integration test that replicates the EXACT API flow from index.py get_valuation()
for MA and V, to trace the Monopoly PE scoring end-to-end.
"""
import sys
import math
sys.path.insert(0, r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\Calculator-Fair-Value')

from scraper.yahoo import get_company_data
from models.scoring import calculate_scoring_reform, calculate_health_score, clean_ratio, clean_percent

def test_ticker(ticker):
    print(f'\n{"="*70}')
    print(f'  INTEGRATION TEST: {ticker}')
    print(f'{"="*70}')
    
    data = get_company_data(ticker)
    if data.get('error'):
        print(f'ERROR: {data["error"]}')
        return
    
    current_price = data.get('current_price') or 0
    shares = data.get('shares_outstanding') or 0
    
    # === REPLICATE index.py data modifications (lines 1060-1482) ===
    
    # Stabilize Revenue Growth (line 1063-1088)
    historical_trends = data.get("historical_trends", [])
    stable_rev_growth = data.get("revenue_growth")
    if historical_trends and len(historical_trends) >= 2:
        try:
            def get_yr_num(h):
                y_str = str(h.get("year", "0"))
                nums = "".join(filter(str.isdigit, y_str))
                return int(nums) if nums else 0
            sorted_trends = sorted(historical_trends, key=get_yr_num, reverse=True)
            reported_revs = [h.get("revenue") for h in sorted_trends if h.get("revenue") and "(Est)" not in str(h.get("year"))]
            if len(reported_revs) >= 2:
                curr_r = reported_revs[0]
                prev_r = reported_revs[1]
                if curr_r and prev_r and prev_r > 0:
                    stable_rev_growth = (curr_r - prev_r) / prev_r
        except: pass
    data["revenue_growth"] = stable_rev_growth
    data["next_3y_rev_growth"] = stable_rev_growth
    
    # Standard field defaults (lines 1420-1482)
    data["roe"] = data.get("roe") or 0
    data["roa"] = data.get("roa") or 0
    data["ebit_margin"] = data.get("operating_margin") or data.get("ebit_margin") or 0
    data["net_margin"] = data.get("net_margin") or 0
    data["bvps_growth"] = data.get("historic_bvps_growth") or 0
    data["next_3y_rev_growth"] = data.get("revenue_growth") or 0
    
    rev_val = data.get("revenue") or 0
    fcf = data.get("fcf") or 0
    data["affo_margin"] = data.get("affo_margin") or (fcf/rev_val if fcf and rev_val > 0 else 0)
    data["affo_growth"] = data.get("historic_fcf_growth") or 0
    
    p_affo = 0
    if fcf and shares and shares > 0 and (fcf/shares) != 0:
        p_affo = current_price / (fcf/shares)
    data["price_to_affo"] = p_affo
    
    mkt_cap_val = (current_price * shares) if (current_price and shares) else 0
    data["fcf_yield"] = (fcf / mkt_cap_val) if (fcf and mkt_cap_val > 0) else 0
    
    if not data.get("ps_ratio") or data["ps_ratio"] == 0:
        data["ps_ratio"] = current_price / (rev_val / (shares or 1)) if rev_val > 0 and shares > 0 else 0
    
    ebitda_val = data.get("ebitda")
    if ebitda_val and ebitda_val > 0:
        debt_val = data.get("total_debt") or 0
        cash_val = data.get("total_cash") or 0
        ev_val = mkt_cap_val + debt_val - cash_val
        data["ev_to_ebitda"] = ev_val / ebitda_val
        data["debt_to_ebitda"] = debt_val / ebitda_val
    else:
        data["ev_to_ebitda"] = 0
        data["debt_to_ebitda"] = 0
    
    # 2Y Revenue CAGR (lines 1472-1481)
    _rev_ests = data.get("rev_estimates") or []
    _est_growths = [float(t["growth"]) for t in _rev_ests if t.get("status") == "estimate" and t.get("growth") is not None]
    if len(_est_growths) >= 2:
        mult = (1 + _est_growths[0]) * (1 + _est_growths[1])
        data["rev_cagr_2y"] = (mult ** 0.5 - 1) if mult >= 0 else ((_est_growths[0] + _est_growths[1]) / 2.0)
    elif len(_est_growths) == 1:
        data["rev_cagr_2y"] = _est_growths[0]
    else:
        data["rev_cagr_2y"] = stable_rev_growth or 0.08
    
    # === BUILD valuation_data_for_scoring (line 1487-1496) ===
    pe_historic = data.get("pe_historic") or data.get("pe_ratio")
    
    valuation_data_for_scoring = {
        "margin_of_safety": 0,  # placeholder - real API calculates this
        "sector_median_peg": 0,
        "sector_median_pe": 0,
        "sector_median_ps": 0,
        "sector_median_ev_ebitda": 0,
        "sector_median_pb": 0,
        "historic_pe": pe_historic if pe_historic else 0,
        "market_cap": shares * current_price if shares and current_price else 0.0
    }
    
    # === REPLICATE calculate_scenario_score("base") (lines 1498-1548) ===
    metrics_copy = data.copy()
    eps_ests = metrics_copy.get("eps_estimates", [])
    rev_ests = metrics_copy.get("rev_estimates", [])
    
    fy1_eps_est = next((e for e in eps_ests if e.get("status") == "estimate"), None)
    fy1_rev_est = next((e for e in rev_ests if e.get("status") == "estimate"), None)
    
    print(f'\n--- FY1 EPS Estimate: {fy1_eps_est}')
    print(f'--- FY1 Rev Estimate: {fy1_rev_est}')
    
    if fy1_eps_est and fy1_eps_est.get("avg"):
        eps_val = fy1_eps_est["avg"]
        if eps_val != 0:
            metrics_copy["forward_pe"] = current_price / eps_val
            metrics_copy["fwd_pe"] = metrics_copy["forward_pe"]
            print(f'--- Recalculated forward_pe: {current_price} / {eps_val} = {metrics_copy["forward_pe"]:.2f}')
    
    if fy1_rev_est and fy1_rev_est.get("avg") and fy1_rev_est.get("avg") > 0:
        rev_val_est = fy1_rev_est["avg"]
        metrics_copy["forward_revenue"] = rev_val_est
        if shares and shares > 0:
            metrics_copy["fwd_ps"] = current_price / (rev_val_est / shares)
            metrics_copy["ps_ratio"] = metrics_copy["fwd_ps"]
    
    ttm_rev = data.get("revenue") or data.get("total_revenue")
    if ttm_rev and ttm_rev > 0 and fy1_rev_est and fy1_rev_est.get("avg"):
        metrics_copy["forward_revenue_growth"] = (fy1_rev_est["avg"] - ttm_rev) / ttm_rev
        metrics_copy["fwd_rev_growth"] = metrics_copy["forward_revenue_growth"]
    
    ttm_eps = data.get("trailing_eps") or data.get("adjusted_eps")
    if ttm_eps and ttm_eps > 0 and fy1_eps_est and fy1_eps_est.get("avg"):
        metrics_copy["eps_growth"] = (fy1_eps_est["avg"] - ttm_eps) / ttm_eps
        print(f'--- Recalculated eps_growth: ({fy1_eps_est["avg"]} - {ttm_eps}) / {ttm_eps} = {metrics_copy["eps_growth"]:.4f}')
    
    # === CALL SCORING (line 1548) ===
    print(f'\n--- Key inputs to scoring:')
    print(f'    forward_pe in metrics: {metrics_copy.get("forward_pe")}')
    print(f'    fwd_pe in metrics: {metrics_copy.get("fwd_pe")}')
    print(f'    historic_pe in val_data: {valuation_data_for_scoring["historic_pe"]}')
    print(f'    roic in metrics: {metrics_copy.get("roic")}')
    print(f'    sector: {metrics_copy.get("sector")}')
    print(f'    industry: {metrics_copy.get("industry")}')
    
    scoring_base = calculate_scoring_reform(valuation_data_for_scoring, metrics_copy)
    
    print(f'\n--- SCORING RESULTS (Base Scenario) ---')
    print(f'    Health Score: {scoring_base["health_score_total"]}')
    print(f'    Buy Score: {scoring_base["good_to_buy_total"]}')
    print(f'\n    Buy Breakdown:')
    for item in scoring_base["buy_breakdown"]:
        marker = " <<<" if "P/E" in item["metric"] else ""
        print(f'      {item["metric"]}: {item["value"]} -> {item["points_awarded"]}/{item["max_points"]}{marker}')

for t in ['MA', 'V']:
    test_ticker(t)
