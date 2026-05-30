import json
from scraper.yahoo import get_company_data

def main():
    data = get_company_data("ADBE")
    print("COMPANY PROFILE:")
    print(json.dumps(data.get("company_profile", {}), indent=2))

main()
