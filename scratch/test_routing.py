import sys
import os

# Add to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scraper.yahoo import get_company_data
from models.scoring import calculate_scoring_reform

ticker = sys.argv[1]

# Simulate backend process
print(f"--- Fetching {ticker} ---")
data = get_company_data(ticker)

metrics = {
    "industry": data.get("industry"),
    "sector": data.get("sector"),
    "business_summary": data.get("business_summary"),
    "roic": data.get("roic"),
    "roe": data.get("roe"),
    "roa": data.get("roa"),
    "current_ratio": data.get("current_ratio"),
    "debt_to_equity": data.get("debt_to_equity"),
    "interest_coverage": data.get("interest_coverage"),
    "market_cap": data.get("market_cap"),
    "eps_growth": data.get("eps_growth"),
    "forward_pe": data.get("forward_pe"),
    "trailing_pe": data.get("pe_ratio"),
    "fwd_pe": data.get("forward_pe"),
    "peg_ratio": data.get("peg_ratio"),
    "price_to_book": data.get("price_to_book"),
    "forward_ev_ebitda": None,
    "fwd_rev_growth": data.get("revenue_growth"),
    "rev_cagr_2y": data.get("revenue_growth"),
    "fwd_dividend_yield": data.get("dividend_yield"),
    "nim": data.get("netInterestMargin"),
    "fintech_total_assets": data.get("fintech_total_assets"),
    "fintech_total_equity": data.get("fintech_total_equity"),
    "fintech_net_interest_income": data.get("fintech_net_interest_income"),
    "fintech_non_interest_expense": data.get("fintech_non_interest_expense"),
    "fintech_gross_profit": data.get("fintech_gross_profit"),
    "ebit_margin": data.get("ebit_margin")
}

val_data = {
    "margin_of_safety": 10.0,
    "sector_median_pe": 15.0,
    "sector_median_ps": 3.0,
    "sector_median_pb": 2.0,
    "sector_median_ev_ebitda": 10.0,
    "sector_median_peg": 1.5,
    "historic_pe": 20.0,
    "historic_ps": 4.0,
    "historic_pb": 3.0,
    "historic_ev_ebitda": 12.0,
    "revenue": data.get("revenue", 0)
}

scores = calculate_scoring_reform(val_data, metrics)
print("\n--- Health Breakdown ---")
for h in scores['health_breakdown']:
    print(h)

print("\n--- Buy Breakdown ---")
for b in scores['buy_breakdown']:
    print(b)
