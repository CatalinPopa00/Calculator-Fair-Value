import sys
sys.path.append('.')
from api.index import get_valuation

class DummyResponse:
    def __init__(self):
        self.headers = {}

res = get_valuation('RHM.DE', DummyResponse(), wacc=None, fast_mode=False, skip_peers=True, force_refresh=True)

print("valuation result keys:")
if isinstance(res, dict):
    print("current_price", res.get("current_price"))
    print("trailing_eps", res.get("company_profile", {}).get("trailing_eps"))
    print("adjusted_eps", res.get("company_profile", {}).get("adjusted_eps"))
    print("pe_ratio", res.get("company_profile", {}).get("current_pe"))
    print("fwd_pe", res.get("company_profile", {}).get("fwd_pe"))
else:
    print(res)
