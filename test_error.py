import traceback
import api.index as idx
from fastapi import Response
try:
    idx.get_valuation('NFLX', Response(), skip_peers=True, force_refresh=True)
except Exception as e:
    print(traceback.format_exc())
