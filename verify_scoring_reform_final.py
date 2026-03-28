import json
import sys
import os

# Add parent dir to path if needed
sys.path.append(os.getcwd())

try:
    from api.models.scoring import calculate_scoring_reform
except ImportError:
    print("Error: Could not import calculate_scoring_reform. Make sure you are in the project root.")
    sys.exit(1)

def test_sector(name, metrics, valuation_data):
    print(f"\n[{name} STOCK RESULTS]")
    results = calculate_scoring_reform(valuation_data, metrics)
    print(json.dumps(results, indent=2))
    
    # Validation
    h_len = len(results['health_breakdown'])
    b_len = len(results['buy_breakdown'])
    h_score = results['health_score_total']
    b_score = results['good_to_buy_total']
    
    if h_len != 6: print(f"FAIL: Health breakdown has {h_len} items (expected 6)")
    if b_len != 6: print(f"FAIL: Buy breakdown has {b_len} items (expected 6)")
    
    # Check for labels
    for item in results['health_breakdown'] + results['buy_breakdown']:
        if not item.get('metric') or item.get('metric') == "undefined":
            print(f"FAIL: Metric name is invalid for {item}")

    return results

# 1. TECH (Default)
tech_metrics = {
    "sector": "Technology",
    "debt_to_equity": 0.5,
    "interest_coverage": 15.0,
    "current_ratio": 1.5,
    "ebit_margin": 25.0,
    "roic": 18.0,
    "fcf_history": [100, 90, 80], # Increasing (newest first)
    "peg_ratio": 0.8,
    "forward_pe": 12.0,
    "ps_ratio": 2.0,
    "fcf": 1000,
    "market_cap": 10000, # 10% FCF Yield
    "revenue_growth": 12.0
}
test_sector("TECH", tech_metrics, {"margin_of_safety": 25.0})

# 2. FINANCIALS
fin_metrics = {
    "sector": "Financial Services",
    "debt_to_equity": 0.5,
    "nim": 3.5,
    "cet1_ratio": 13.5,
    "roe": 18.0,
    "roa": 1.8,
    "bvps_growth": 10.0,
    "peg_ratio": 0.8,
    "pe_ratio": 9.0,
    "price_to_book": 0.9,
    "dividend_yield": 4.5,
    "next_3y_rev_est": 12.0
}
test_sector("FINANCIAL", fin_metrics, {"margin_of_safety": 25.0})

# 3. REITs
reit_metrics = {
    "sector": "Real Estate",
    "debt_to_equity": 0.5,
    "interest_coverage": 15.0,
    "debt_to_ebitda": 5.0,
    "affo_margin": 55.0,
    "roic": 18.0,
    "affo_growth": 6.0,
    "peg_ratio": 1.2, # < 1.5 is 15 pts for REIT!
    "price_to_affo": 14.0,
    "dividend_yield": 6.0,
    "fcf": 1000,
    "market_cap": 10000,
    "next_3y_rev_est": 6.0 # > 5% is 10 pts for REIT!
}
test_sector("REIT", reit_metrics, {"margin_of_safety": 25.0})

print("\n--- FINAL VERIFICATION COMPLETE ---")
