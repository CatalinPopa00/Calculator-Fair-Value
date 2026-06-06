import api.index as idx
from fastapi import Response
try:
    data = idx.get_valuation('ADBE', Response(), skip_peers=True, force_refresh=True)
    print('5y cagr custom:', data['company_profile'].get('cagr_5y_custom'))
except Exception as e:
    import traceback
    print(traceback.format_exc())
