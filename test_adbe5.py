import api.index as idx
from fastapi import Response
import json
try:
    data = idx.get_valuation('ADBE', Response(), skip_peers=True, force_refresh=True)
    prof = data['company_profile']
    print('cagr_5y_custom:', prof.get('cagr_5y_custom'))
    print('forward_pe_custom:', prof.get('forward_pe_custom'))
    print('forward_pe:', prof.get('forward_pe'))
    print('price:', prof.get('price'))
    print('fwd_eps:', prof.get('fwd_eps'))
except Exception as e:
    import traceback
    print(traceback.format_exc())
