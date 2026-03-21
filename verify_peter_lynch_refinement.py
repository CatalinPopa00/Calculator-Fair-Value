import sys
import os
import math
sys.path.append(os.path.join(os.getcwd(), 'api'))

from models.valuation import calculate_peter_lynch

def test_peter_math():
    print("Testing Peter Lynch Math Refinement...")
    current_price = 100.0
    trailing_eps = 5.0
    eps_growth = 0.10 # 10%
    pe_historic = 25.0
    sector_pe = 22.0
    
    # Expected:
    # fwd_eps = 5 * (1.1^3) = 5 * 1.331 = 6.655
    # fwd_pe = 100 / 6.655 = 15.026
    # fair_value = 6.655 * 25 = 166.375
    # fair_value_pe_20 = 6.655 * 20 = 133.1
    # fair_value_sector_pe = 6.655 * 22 = 146.41
    
    res = calculate_peter_lynch(current_price, trailing_eps, eps_growth, pe_historic, sector_pe)
    print(f"Result: {res}")
    
    assert math.isclose(res['fwd_eps'], 6.655, rel_tol=1e-4)
    assert math.isclose(res['fair_value_pe_20'], 133.1, rel_tol=1e-4)
    assert res['trailing_eps'] == 5.0
    assert res['eps_growth_estimated'] == 0.10
    print("Math Verification Passed!")

if __name__ == "__main__":
    test_peter_math()
