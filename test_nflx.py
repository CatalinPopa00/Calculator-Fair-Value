import api.index as idx; from fastapi import Response; print(idx.get_valuation('NFLX', Response(), skip_peers=True, force_refresh=False).keys())
