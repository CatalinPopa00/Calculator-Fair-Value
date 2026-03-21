from api.index import get_valuation
import sys

try:
    data = get_valuation("AAPL")
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
