from models.scoring import calculate_health_score, calculate_buy_score

def test_reit():
    print("TEST: Real Estate (REIT)")
    metrics = {
        'sector': 'Real Estate',
        'debt_to_equity': 1.8, # Threshold < 2.0x (20 pts)
        'fcf_history': [500, 400, 300], # Positive OCF (20 pts)
        'ebit_margin': 0.45, # Threshold > 40% (15 pts)
        'current_ratio': 1.1, # Threshold >= 1.0 (15 pts)
        'roic': 0.08,
        'interest_coverage': 4.0,
        'dividend_yield': 0.05, # > 4% (15 pts)
        'market_cap': 10000,
        'fcf': 400
    }
    h = calculate_health_score(metrics)
    b = calculate_buy_score({'margin_of_safety': 20.0}, metrics)
    print(f"Health Total: {h['total']}")
    for i in h['breakdown']:
        print(f"Health - {i['metric']}: {i['points_awarded']} pts ({i['value']})")
    print(f"Buy Total: {b['total']}")
    for i in b['breakdown']:
        print(f"Buy - {i['metric']}: {i['points_awarded']} pts ({i['value']})")

def test_utilities():
    print("\nTEST: Utilities")
    metrics = {
        'sector': 'Utilities',
        'debt_to_equity': 1.2, # Threshold < 1.5x (20 pts)
        'current_ratio': 0.85, # Threshold > 0.8 (15 pts)
        'fcf_history': [-100], # Neutral (10 pts)
        'ebit_margin': 0.20,
        'roic': 0.05,
        'interest_coverage': 3.5,
        'dividend_yield': 0.035, # > 3% (15 pts)
        'market_cap': 5000,
        'fcf': -100
    }
    h = calculate_health_score(metrics)
    b = calculate_buy_score({'margin_of_safety': 10.0}, metrics)
    print(f"Health Total: {h['total']}")
    for i in h['breakdown']:
        print(f"Health - {i['metric']}: {i['points_awarded']} pts ({i['value']})")
    print(f"Buy Total: {b['total']}")
    for i in b['breakdown']:
        print(f"Buy - {i['metric']}: {i['points_awarded']} pts ({i['value']})")

def test_consum_def():
    print("\nTEST: Consumer Defensive")
    metrics = {
        'sector': 'Consumer Defensive',
        'ebit_margin': 0.07, # > 6% (15 pts)
        'roic': 0.12, # > 10% (15 pts)
        'debt_to_equity': 0.4,
        'fcf_history': [100],
        'current_ratio': 1.2,
        'interest_coverage': 10.0
    }
    h = calculate_health_score(metrics)
    print(f"Health Total: {h['total']}")
    for i in h['breakdown']:
        print(f"Health - {i['metric']}: {i['points_awarded']} pts ({i['value']})")

def test_tech_growth():
    print("\nTEST: Technology Growth Bonus")
    metrics = {
        'sector': 'Technology',
        'fwd_ps': 6.5, # > 5.0 (Expensive)
        'next_3y_rev_est': 0.25, # > 20% (Bonus)
        'debt_to_equity': 0.2,
        'peg_ratio': 1.2,
        'fcf': 5000,
        'market_cap': 100000,
        'eps_growth': 0.20
    }
    b = calculate_buy_score({'margin_of_safety': -5.0}, metrics)
    print(f"Buy Total: {b['total']}")
    for i in b['breakdown']:
        print(f"Buy - {i['metric']}: {i['points_awarded']} pts ({i['value']})")

if __name__ == "__main__":
    test_reit()
    test_utilities()
    test_consum_def()
    test_tech_growth()
