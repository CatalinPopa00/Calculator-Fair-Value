from api.index import get_valuation
import json

try:
    data = get_valuation("ADBE")
    print(json.dumps(data["formula_data"]["peter_lynch"], indent=2))
    print(json.dumps(data["formula_data"]["peg"], indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
