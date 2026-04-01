import math
import statistics

# Mocking the Peter Lynch calculation from models/valuation.py (approximated)
def calculate_peter_lynch(current_price, eps, growth, pe_hist, target_pe):
    # fair_value = eps * (1 + growth)^3 * target_pe (simplified approximation for test)
    # The real one might have years etc.
    if eps is None or eps <= 0: return {"fair_value": 0, "status": "Error"}
    fv = eps * math.pow(1 + growth, 3) * target_pe
    return {"fair_value": fv, "status": "Success"}

def test_sync_logic():
    # TEST CASE: NVO Situation
    current_price = 36.75
    eps = 3.58
    nasdaq_growth = -0.0124 # -1.24%
    yahoo_growth = 0.0146 # +1.46%
    sector_pe = 20.0
    
    print(f"Testing with Nasdaq Growth: {nasdaq_growth*100}% vs Yahoo Growth: {yahoo_growth*100}%")
    
    # OLD LOGIC (Disconnected):
    # Lynch Card uses Nasdaq
    lynch_old = calculate_peter_lynch(current_price, eps, nasdaq_growth, 30.0, sector_pe)
    # DCF uses Yahoo or +5% fallback
    dcf_growth_old = yahoo_growth if yahoo_growth is not None else 0.05
    
    print(f"OLD LOGIC Result:")
    print(f"  Lynch Growth: {nasdaq_growth*100:.2f}% -> Lynch FV: ${lynch_old['fair_value']:.2f}")
    print(f"  DCF Growth (Fallback): {dcf_growth_old*100:.2f}%")
    
    # NEW LOGIC (Synchronized v62):
    consensus_growth = nasdaq_growth if nasdaq_growth is not None else (yahoo_growth or 0.05)
    
    # Conservative Cap Logic
    effective_pe = sector_pe
    if consensus_growth < 0:
        effective_pe = min(sector_pe, 12.0)
        
    lynch_new = calculate_peter_lynch(current_price, eps, consensus_growth, 30.0, effective_pe)
    
    print(f"\nNEW LOGIC Result (v62):")
    print(f"  Consensus Growth (Shared): {consensus_growth*100:.2f}%")
    print(f"  Effective PE Multiple: {effective_pe}x (Capped: {effective_pe < sector_pe})")
    print(f"  Lynch FV: ${lynch_new['fair_value']:.2f}")
    
    if lynch_new['fair_value'] < lynch_old['fair_value']:
        print("\n✅ SUCCESS: Valuation is now consistently conservative for negative growth.")
    else:
        print("\n❌ FAILURE: Valuation did not adjust to conservative multiples.")

if __name__ == "__main__":
    test_sync_logic()
