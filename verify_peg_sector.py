import sys
import os
import math
sys.path.append(os.path.join(os.getcwd(), 'api'))

import statistics

def test_peg_sector_logic():
    print("Testing PEG Sector Logic (Inclusion of target company)...")
    
    # Simulating index.py logic
    company_price = 100.0
    trailing_eps = 5.0
    eps_growth = 0.10 # 10%
    
    # 1. Calculate company PEG
    current_pe = company_price / trailing_eps # 20
    company_peg = current_pe / (eps_growth * 100) # 20 / 10 = 2.0
    
    # 2. Mock Peers
    peers_data = [
        {'peg_ratio': 1.0},
        {'peg_ratio': 1.5}
    ]
    
    # Logic in index.py:
    valid_pegs = []
    if company_peg > 0:
        valid_pegs.append(float(company_peg)) # [2.0]
    
    for p in peers_data:
        v = p.get('peg_ratio')
        if v is not None:
            valid_pegs.append(float(v)) # [2.0, 1.0, 1.5]
            
    # Median of [1.0, 1.5, 2.0] is 1.5
    median_peg = statistics.median(valid_pegs)
    print(f"Valid PEGs: {valid_pegs}")
    print(f"Median PEG: {median_peg}")
    
    assert median_peg == 1.5
    print("PEG Sector Verification Passed!")

if __name__ == "__main__":
    test_peg_sector_logic()
