import api.index as idx
from fastapi import Response
try:
    data = idx.get_valuation('ADBE', Response(), skip_peers=True, force_refresh=True)
    print('EPS Est:', data['company_profile'].get('eps_growth_estimated'))
except Exception as e:
    import traceback
    print(traceback.format_exc())
