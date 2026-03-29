import os, sys, json
sys.path.insert(0, os.path.abspath('.'))
from api.scraper.yahoo import get_company_data

data = get_company_data("GOOGL")
print(f"Name: {data.get('name')}")
print(f"Price: {data.get('current_price')}")
print(f"PE Ratio: {data.get('pe_ratio')}")
print(f"EPS: {data.get('trailing_eps')}")
print(f"Dividend Yield: {data.get('dividend_yield')}")
print(json.dumps(data, indent=2))
