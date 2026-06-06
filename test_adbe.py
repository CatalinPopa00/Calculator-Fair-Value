import api.index as idx
from fastapi import Response
import json
try:
    data = idx.get_valuation('ADBE', Response(), skip_peers=True, force_refresh=True)
    print(json.dumps(data.get('scoring_results', {}).get('base', {}).get('buy_breakdown', []), indent=2))
except Exception as e:
    import traceback
    print(traceback.format_exc())
