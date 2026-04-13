import sys
sys.path.append('.')
from api.scraper.yahoo import get_lightweight_company_data

def test_strict():
    candidates = ['AMD', 'NVDA', 'AVGO', 'MSFT', 'ORCL', 'SNOW', 'CRM', 'GOOG']
    target_ind = 'Software—Infrastructure'
    for c in candidates:
        try:
            data = get_lightweight_company_data(c)
            # print(f"{c}: {data.get('industry')} / {data.get('sector')}")
            if data and data.get('industry') == target_ind:
                print(f"MATCH: {c}")
        except: pass
test_strict()
