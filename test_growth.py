import sys
sys.path.append('.')
from models.scoring import calculate_scoring_reform

def test_industrials():
    print("Testing Industrials...")
    metrics = {
        'sector': 'Industrials',
        'industry': 'Aerospace & Defense',
        'ebit_margin': 0.06, # 6%
    }
    res = calculate_scoring_reform({'margin_of_safety': 10}, metrics)
    h_break = res['health_breakdown']
    ebit_score = next(x for x in h_break if x['metric'] == 'EBIT Margin')
    print(f"Industrials EBIT: {ebit_score['points_awarded']}")

def test_growth_override():
    print("Testing Growth Override...")
    metrics = {
        'sector': 'Technology',
        'industry': 'Software',
        'trailing_pe': 100, # Very high PE, normally 0 points
        'ev_to_ebitda': 80, # Very high EV/EBITDA, normally 0 points
        'peg_ratio': 1.0,   # <= 1.2
        'revenue_growth': 0.25, # 25%
    }
    res = calculate_scoring_reform({'margin_of_safety': 10}, metrics)
    b_break = res['buy_breakdown']
    
    pe_score = next(x for x in b_break if 'P/E Ratio' in x['metric'])
    ev_score = next(x for x in b_break if 'EV / EBITDA' in x['metric'])
    
    print(f"Growth Override P/E Score: {pe_score['points_awarded']}")
    print(f"Growth Override EV/EBITDA Score: {ev_score['points_awarded']}")

if __name__ == '__main__':
    test_industrials()
    test_growth_override()
