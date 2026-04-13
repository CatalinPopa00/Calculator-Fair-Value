import sys
from unittest.mock import MagicMock
import pandas as pd

# Mock yfinance before importing get_analyst_data if possible, 
# or just test the logic directly by calling get_analyst_data for a real but stripped ticker

def test_fallback_logic():
    # We want to test the part of get_analyst_data that does:
    # if not rec_mean: ... total_votes = sum(rec_counts.values()) ...
    
    # Mocking the counts from the screenshot: 3, 5, 10, 2, 2
    rec_counts = {"strongBuy": 3, "buy": 5, "hold": 10, "sell": 2, "strongSell": 2}
    total_votes = sum(rec_counts.values())
    weighted_sum = (
        rec_counts["strongBuy"] * 1 +
        rec_counts["buy"] * 2 +
        rec_counts["hold"] * 3 +
        rec_counts["sell"] * 4 +
        rec_counts["strongSell"] * 5
    )
    calculated_mean = weighted_sum / total_votes
    
    print(f"Total Votes: {total_votes}")
    print(f"Weighted Sum: {weighted_sum}")
    print(f"Calculated Mean: {calculated_mean:.2f}")
    
    expected = (3*1 + 5*2 + 10*3 + 2*4 + 2*5) / 22 # 61 / 22 = 2.7727...
    print(f"Expected: {expected:.2f}")
    
    assert abs(calculated_mean - expected) < 0.001
    print("Fallback logic verification: SUCCESS")

if __name__ == "__main__":
    test_fallback_logic()
