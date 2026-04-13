import sys
import os
import math

# Add api to path
sys.path.append(os.path.join(os.getcwd(), 'api'))

from api.models.scoring import calculate_health_score, calculate_buy_score

def test_scoring():
    print("--- Testing New Scoring Logic ---")
    
    # 1. Mock Data
    metrics = {
        "debt_to_equity": 0.4,       # Vc
        "roic": 0.20,                # Vc
        "interest_coverage": 10.0,   # Vc
        "current_ratio": 2.0,        # Vc
        "ebit_margin": 0.25,         # Vc
        "historic_fcf_growth": 0.15, # Vc
        "peg_ratio": 0.8,            # Vc
        "fcf_yield": 8.0,            # Vc
        "forward_pe": 15.0,          # Vc
        "next_3y_rev_est": 0.12      # Vc
    }
    
    sector_avg = {
        "debt_to_equity": 0.5,       # Vs (Lower is better: Vc < Vs*0.9 => 100%)
        "roic": 0.15,                # Vs (Higher is better: Vc > Vs*1.1 => 100%)
        "interest_coverage": 5.0,    # Vs
        "current_ratio": 1.5,        # Vs
        "ebit_margin": 0.20,         # Vs
        "historic_fcf_growth": 0.10, # Vs
        "peg_ratio": 1.2,            # Vs
        "fcf_yield": 5.0,            # Vs
        "forward_pe": 20.0,          # Vs
        "next_3y_rev_est": 0.10      # Vs
    }
    
    valuation_data = {
        "margin_of_safety": 25.0     # Absolute Rule (>= 20% => 100%)
    }

    # 2. Test Health Score
    print("\nTesting Health Score...")
    h_res = calculate_health_score(metrics, sector_avg)
    print(f"Health Total: {h_res['total']}/100")
    print(f"Strengths: {h_res['top_strengths']}")
    print(f"Risks: {h_res['risk_factors']}")
    assert h_res['total'] == 100, f"Expected 100, got {h_res['total']}"

    # 3. Test Buy Score
    print("\nTesting Buy Score...")
    b_res = calculate_buy_score(metrics, valuation_data, sector_avg)
    print(f"Buy Total: {b_res['total']}/100")
    print(f"Strengths: {b_res['top_strengths']}")
    print(f"Risks: {b_res['risk_factors']}")
    assert b_res['total'] == 100, f"Expected 100, got {b_res['total']}"

    # 4. Test Red Flags
    print("\nTesting Red Flags...")
    metrics_bad = metrics.copy()
    metrics_bad['debt_to_equity'] = 4.0 # Red Flag > 3.0
    h_bad = calculate_health_score(metrics_bad, sector_avg)
    print(f"Bad Health Total (D/E=4.0): {h_bad['total']} (Expected max 40)")
    assert h_bad['total'] <= 40

    valuation_bad = {"margin_of_safety": -25.0} # Red Flag < -20%
    b_bad = calculate_buy_score(metrics, valuation_bad, sector_avg)
    print(f"Bad Buy Total (MoS=-25%): {b_bad['total']} (Expected max 40)")
    assert b_bad['total'] <= 40

    print("\n--- All Tests Passed! ---")

if __name__ == "__main__":
    try:
        test_scoring()
    except Exception as e:
        print(f"Test Failed: {e}")
        sys.exit(1)
