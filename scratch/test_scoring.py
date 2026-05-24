import sys
sys.path.append(r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value")

from models.scoring import calculate_scoring_reform
import json

def test_company(ticker, sector, industry, valuation_data, metrics):
    res = calculate_scoring_reform(valuation_data, metrics)
    print(f"\n[{ticker}] Sector: {sector} | Buy Score: {res['good_to_buy_total']}/100")
    for item in res['buy_breakdown']:
        print(f"  - {item['metric']}: {item['value']} => {item['points_awarded']}/{item['max_points']}")

print("--- Testing Forward-First Scoring ---")

# RHM
test_company("RHM", "Industrials", "Aerospace & Defense",
             {"sector": "Industrials", "industry": "Aerospace & Defense", "margin_of_safety": 5.0},
             {
                 "revenue_growth": 25.0,
                 "eps_growth_5y_consensus": 30.0,
                 "forward_pe": 16.0,
                 "trailing_pe": 40.0,
                 "ev_to_ebitda": 11.0,
                 "price_to_book": 2.5,
                 "peg_ratio": 0.8
             })

# JPM
test_company("JPM", "Financials", "Banks - Diversified",
             {"sector": "Financials", "industry": "Banks - Diversified", "margin_of_safety": 12.0},
             {
                 "eps_growth_5y_consensus": 8.0,
                 "forward_pe": 12.0,
                 "price_to_book": 1.4,
                 "fwd_dividend_yield": 3.5,
                 "peg_ratio": 1.1,
                 "nim": 3.2, "cet1_ratio": 13.0, "roe": 16.0, "roa": 1.2, "bvps_growth": 10.0
             })

# O (REIT)
test_company("O", "Real Estate", "REIT - Retail",
             {"sector": "Real Estate", "industry": "REIT - Retail", "margin_of_safety": 10.0},
             {
                 "affo_growth": 5.0,
                 "price_to_affo": 14.0,
                 "affo_yield": 7.0,
                 "fwd_dividend_yield": 5.5,
                 "debt_to_ebitda": 5.5,
                 "interest_coverage": 4.0,
                 "current_ratio": 1.2,
                 "dividend_streak": 25
             })
