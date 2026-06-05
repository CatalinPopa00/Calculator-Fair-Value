from scraper.yahoo import get_company_data
import json

res = get_company_data('ADBE', force_refresh=True)
prof = res.get('profile', {})

print('ADBE FWD PE:', prof.get('fwd_pe'))
print('ADBE FWD EPS:', prof.get('fwd_eps_fy1'))
print('ADBE PRICE:', prof.get('price'))
print('ADBE PEG:', prof.get('peg_ratio'))

peers = res.get('peers', [])
for p in peers:
    print(f"{p.get('ticker')}: FWD PE={p.get('forward_pe_custom')}, PEG={p.get('peg_ratio')}, CAGR={p.get('cagr_5y_custom')}")
