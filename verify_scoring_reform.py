import json
from api.models.scoring import calculate_scoring_reform

def test_scoring():
    print("--- TESTING SCORING REFORM (REFINED) ---")
    
    # Mock data for a standard Tech stock
    valuation_data = {
        "margin_of_safety": 25.0
    }
    
    tech_metrics = {
        "sector": "Information Technology",
        "debt_to_equity": 0.5,       # < 0.8 -> 20 pts
        "interest_coverage": 15.0,  # > 10 -> 15 pts
        "current_ratio": 1.5,       # > 1.2 -> 15 pts
        "ebit_margin": 25.0,        # > 20 -> 15 pts
        "roic": 18.0,               # > 15 -> 20 pts
        "fcf_history": [100, 90, 80], # Increasing -> 15 pts
        "next_3y_rev_est": 12.0,    # > 10 -> 10 pts (New Threshold)
        "revenue_growth": 12.0,
        "peg_ratio": 0.8,           # < 1.0 -> 15 pts (New Threshold)
        "forward_pe": 12.0,         # < 15 -> 15 pts
        "fwd_ps": 2.0,              # < 3.0 -> 15 pts
        "market_cap": 1000,
        "fcf": 100                  # FCF Yield = 10% > 7% -> 15 pts
    }
    
    # Expected Tech Score:
    # Health: 20(DE) + 15(IC) + 15(CR) + 15(EBIT) + 20(ROIC) + 15(FCF) = 100
    # Buy: 30(MOS) + 15(PEG) + 15(PE) + 15(PS) + 15(FCFY) + 10(RevG) = 100
    
    res_tech = calculate_scoring_reform(valuation_data, tech_metrics)
    print("\n[TECH STOCK RESULTS]")
    print(json.dumps(res_tech, indent=2))
    
    assert res_tech["health_score_total"] == 100, f"Expected 100 Health, got {res_tech['health_score_total']}"
    assert res_tech["good_to_buy_total"] == 100, f"Expected 100 Buy, got {res_tech['good_to_buy_total']}"
    
    # Mock data for a Financial stock
    fin_metrics = {
        "sector": "Financial Services",
        "debt_to_equity": 0.5,
        "cet1_ratio": 13.5,          # > 12 -> 15 pts
        "nim": 3.5,                  # > 3.0 -> 15 pts
        "roe": 18.0,                 # > 15 -> 15 pts
        "roa": 1.8,                  # > 1.5 -> 20 pts
        "historic_bvps_growth": 10.0, # > 8 -> 15 pts
        "peg_ratio": 0.8,
        "forward_pe": 9.0,
        "price_to_book": 0.9,        # < 1.2 -> 15 pts
        "dividend_yield": 4.5,       # > 4.0 -> 15 pts
        "next_3y_rev_est": 12.0,
        "margin_of_safety": 25.0
    }
    
    res_fin = calculate_scoring_reform(valuation_data, fin_metrics)
    print("\n[FINANCIAL STOCK RESULTS]")
    print(json.dumps(res_fin, indent=2))
    
    # Check if BVPS Growth is used instead of FCF Trend
    found_bvps = any(item["metric"] == "BVPS Growth" for item in res_fin["health_breakdown"])
    assert found_bvps, "BVPS Growth should be in Financial breakdown"
    
    # Mock data for a REIT
    reit_metrics = {
        "sector": "Real Estate",
        "debt_to_equity": 0.5,
        "interest_coverage": 15.0,
        "total_debt": 500,
        "ebitda": 100,               # D/EBITDA = 5.0 < 5.5 -> 15 pts
        "affo_margin": 55.0,         # > 50% -> 15 pts
        "roic": 18.0,
        "affo_growth": 6.0,          # > 5% -> 15 pts
        "dividend_yield": 6.0,       # > 5% -> 15 pts (Fwd PS Substitution)
        "fcf": 100,
        "market_cap": 1000,
        "peg_ratio": 0.8,
        "forward_pe": 12.0,
        "price_to_affo": 14.0,       # < 15x -> 15 pts
        "next_3y_rev_est": 12.0,
        "margin_of_safety": 25.0
    }
    
    res_reit = calculate_scoring_reform(valuation_data, reit_metrics)
    print("\n[REIT RESULTS]")
    print(json.dumps(res_reit, indent=2))
    
    found_dte = any(item["metric"] == "Debt-to-EBITDA" for item in res_reit["health_breakdown"])
    assert found_dte, "Debt-to-EBITDA should be in REIT breakdown"

    print("\n--- ALL TESTS PASSED ---")

if __name__ == "__main__":
    test_scoring()
