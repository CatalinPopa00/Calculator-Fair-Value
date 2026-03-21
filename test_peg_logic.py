from api.models.valuation import calculate_peg_fair_value
import math

def test_peg():
    # current_price, company_peg, industry_peg
    res = calculate_peg_fair_value(100.0, 2.0, 1.5)
    # 100 * (1.5 / 2.0) = 100 * 0.75 = 75.0
    print(f"Fair Value (1.5 / 2.0): {res}")
    assert res == 75.0
    
    res = calculate_peg_fair_value(100.0, 0.5, 1.0)
    # 100 * (1.0 / 0.5) = 200.0
    print(f"Fair Value (1.0 / 0.5): {res}")
    assert res == 200.0
    
    res = calculate_peg_fair_value(100.0, 0, 1.0)
    print(f"Fair Value (0 PEG): {res}")
    assert res is None
    
    print("Logic Tests: SUCCESS")

if __name__ == "__main__":
    test_peg()
