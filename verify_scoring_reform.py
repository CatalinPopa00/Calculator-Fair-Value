import os
import sys
import json

# Add current directory to path so we can import modules
sys.path.append(os.getcwd())

from api.models.scoring import calculate_scoring_reform, clean_percent

def test_scoring():
    print("--- TESTING SCORING REFORM ---")
    
    # Mock data for a standard stock (Technology)
    tech_metrics = {
        "sector": "Technology",
        "debt_to_equity": 0.5,       # < 0.8x -> 20 pts
        "interest_coverage": 15.0,   # > 10x -> 15 pts
        "current_ratio": 1.5,        # > 1.2x -> 15 pts
        "ebit_margin": 0.25,         # 25% > 20% -> 15 pts (cleaned to 25.0)
        "roic": 0.18,                # 18% > 15% -> 20 pts (cleaned to 18.0)
        "fcf_history": [100, 80, 60], # Increasing -> 15 pts
        "fcf": 100,
        "market_cap": 1000,          # Yield 10% > 7% -> 15 pts
        "peg_ratio": 0.8,            # < 1.0x -> 20 pts
        "forward_pe": 12.0,          # < 15x -> 15 pts
        "fwd_ps": 2.0,               # < 3.0x -> 15 pts
        "next_3y_rev_est": 0.12,      # 12% > 10% -> 20 pts
        "margin_of_safety": 25.0     # > 20% -> 30 pts
    }
    
    valuation_data = {"margin_of_safety": 25.0}
    
    res = calculate_scoring_reform(valuation_data, tech_metrics)
    print("\n[TECH STOCK RESULTS]")
    print(json.dumps(res, indent=2))
    
    assert res["health_score_total"] == 100
    assert res["good_to_buy_total"] == 115 # Wait, 30+20+15+15+15+20 = 115? 
    # Let's re-read the prompt's Good to Buy points:
    # MOS(30), PEG(20), Fwd PE(15), Fwd PS(15), FCF Yield(15), Rev Growth(20)
    # 30+20+15+15+15+20 = 115. 
    # The prompt says "(100 pct)" at the start of Good to Buy Score. 
    # But the points sum to 115. I should probably adjust them or keep them as requested.
    # If the user says 100 pct and then gives 115 pts, I'll follow the pts.
    
    # Mock data for a Financial stock
    fin_metrics = {
        "sector": "Financial Services",
        "debt_to_equity": 0.5,
        "cet1_ratio": 13.5,          # >12% -> 15 pts
        "nim": 3.5,                  # >3% -> 15 pts
        "ebit_margin": 0.25,         
        "roic": 0.18,                
        "historic_bvps_growth": 10.0, # >8% -> 15 pts
        "fcf": 100,
        "market_cap": 1000,
        "peg_ratio": 0.8,
        "forward_pe": 9.0,           # < 10x -> 15 pts (PE substitution)
        "next_3y_rev_est": 0.12,
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
        "total_debt": 500,
        "ebitda": 100,               # D/EBITDA = 5.0 < 5.5 -> 15 pts
        "affo_margin": 55.0,         # > 50% -> 15 pts
        "roic": 18.0,
        "affo_growth": 6.0,          # > 5% -> 15 pts
        "fcf": 100,
        "market_cap": 1000,
        "peg_ratio": 0.8,
        "forward_pe": 12.0,
        "price_to_affo": 14.0,       # < 15x -> 15 pts
        "next_3y_rev_est": 0.12,
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
