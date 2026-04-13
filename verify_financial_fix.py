import sys
import os

# Add the current directory to sys.path to import local modules
sys.path.append(os.getcwd())

from api.models.scoring import calculate_health_score, calculate_buy_score

def test_financial_scoring():
    print("--- Testing Financial Services Scoring Refinements ---")
    
    financial_metrics = {
        "ticker": "SOFI",
        "sector": "Financial Services",
        "price_to_book": 1.6, # Threshold 1.5 for 20 pts, 2.5 for 10 pts
        "roe": 0.09, # Threshold 0.08 for 15 pts
        "roa": 0.009, # Threshold 0.008 for 15 pts
        "fcf_history": [-1000000, -500000, -200000],
        "current_ratio": 0.5,
        "interest_coverage": 0.4,
        # Buy score metrics
        "peg_ratio": 0.74,
        "fwd_ps": 5.3,
        "fcf": -1000000,
        "market_cap": 22650000000,
        "next_3y_rev_est": 0.15,
        "eps_growth": 0.25,
        "dividend_yield": 0.0
    }

    valuation_data = {
        "margin_of_safety": 31.05
    }

    print("\n[Health Score Verification]")
    health = calculate_health_score(financial_metrics)
    print(f"Total Health Score: {health['total']}/100")
    for item in health['breakdown']:
        print(f" - {item['name']}: {item['value']} | {item['points']}/{item['max_points']} pts")

    print("\n[Buy Score Verification]")
    buy = calculate_buy_score(valuation_data, financial_metrics)
    print(f"Total Buy Score: {buy['total']}/100")
    for item in buy['breakdown']:
        print(f" - {item['name']}: {item['value']} | {item['points']}/{item['max_points']} pts")

    # Expectations:
    # Health:
    # Debt-to-Equity: Sector Exempt (20/20)
    # FCF Trend: Sector Exempt (10/20)
    # Current Ratio: Sector Exempt (15/15)
    # ROIC: Sector Exempt (ROE Priority) (10/15)
    # Interest Coverage: Sector Exempt (15/15)
    # EBIT Margin: Standard thresholds (10/15 or 15/15)

    print("\n--- End of Test ---")

if __name__ == "__main__":
    test_financial_scoring()
