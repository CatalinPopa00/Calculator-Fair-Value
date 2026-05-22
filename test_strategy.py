import sys
sys.path.append('.')
from models.scoring import calculate_scoring_reform

def test_retail_buyback():
    print("Testing Retail Buyback Exception...")
    metrics = {
        'sector': 'Consumer Cyclical',
        'industry': 'Home Improvement Retail',
        'debt_to_equity': 5.0, # High D/E
        'total_equity': -100,  # Negative Equity
        'roic': 18.0,          # > 15
        'fcf_trend': 'Growing',
        'current_price': 100
    }
    val_data = {'margin_of_safety': 10}
    res = calculate_scoring_reform(val_data, metrics)
    h_break = res['health_breakdown']
    de_score = next(x for x in h_break if x['metric'] == 'Debt-to-Equity')
    print(f"Retail D/E score: {de_score['points_awarded']}/{de_score['max_points']}")

def test_utilities():
    print("Testing Utilities Exception...")
    metrics = {
        'sector': 'Utilities',
        'industry': 'Utilities - Regulated',
        'debt_to_equity': 2.5, # Between 2 and 3
        'current_ratio': 0.6,  # >= 0.5
        'roe': 9.0,            # >= 8
        'current_price': 100
    }
    val_data = {'margin_of_safety': 10}
    res = calculate_scoring_reform(val_data, metrics)
    h_break = res['health_breakdown']
    de_score = next(x for x in h_break if x['metric'] == 'Debt-to-Equity')
    cr_score = next(x for x in h_break if x['metric'] == 'Current Ratio')
    roe_score = next(x for x in h_break if x['metric'] == 'ROE')
    
    # Should not have ROIC
    has_roic = any(x['metric'] == 'ROIC' for x in h_break)
    
    print(f"Utilities D/E: {de_score['points_awarded']}")
    print(f"Utilities CR: {cr_score['points_awarded']}")
    print(f"Utilities ROE: {roe_score['points_awarded']}")
    print(f"Utilities has ROIC? {has_roic}")

if __name__ == '__main__':
    test_retail_buyback()
    test_utilities()
