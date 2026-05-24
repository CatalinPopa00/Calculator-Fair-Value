import os, sys, json
sys.path.append(os.path.dirname(__file__))
from scraper.yahoo import get_company_data
data = get_company_data('INTU', fast_mode=False)
print("historic_pe:", data.get('pe_historic'))
print("pe_ratio:", data.get('pe_ratio'))
print("trailingPE:", data.get('trailingPE'))
print("rev_estimates:", json.dumps(data.get('rev_estimates', []), indent=2))
