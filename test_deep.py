import api.index as idx; from fastapi import Response
print(idx.get_valuation('ADBE', Response(), skip_peers=True))
