import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from index import get_company_data
import json

data = get_company_data("CELH")
peg_data = data.get("formula_data", {}).get("peg", {})
print("Company PEG:", peg_data.get("current_peg"))
print("Industry PEG:", peg_data.get("industry_peg"))
