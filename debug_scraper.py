from api.scraper.yahoo import get_company_data
import sys

try:
    data = get_company_data("AAPL")
    print("SUCCESS")
    print("3y eps:", data.get("eps_growth_3y"))
    print("5y eps:", data.get("eps_growth_5y"))
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
