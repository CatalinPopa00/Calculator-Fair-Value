import sys, os
sys.path.insert(0, os.getcwd())
from api.scraper.yahoo import get_company_data

data = get_company_data("ADBE")
print(f"eps_growth: {data.get('eps_growth')}")
print(f"eps_growth_period: {data.get('eps_growth_period')}")
print(f"trailing_eps: {data.get('trailing_eps')}")
print(f"adjusted_eps: {data.get('adjusted_eps')}")
print(f"forward_eps: {data.get('forward_eps')}")
print(f"pe_ratio: {data.get('pe_ratio')}")
print(f"forward_pe: {data.get('forward_pe')}")
