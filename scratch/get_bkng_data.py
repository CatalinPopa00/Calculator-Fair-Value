import sys
import os
import json
from scraper.yahoo import get_company_data

try:
    print("Fetching BKNG company data...")
    data = get_company_data("BKNG")
    # Extract only what we need for growth calculation to keep the output readable
    rev_estimates = data.get("rev_estimates", [])
    company_profile = data.get("company_profile", {})
    
    output = {
        "rev_estimates": rev_estimates,
        "company_profile": {
            "revenue_growth": company_profile.get("revenue_growth")
        }
    }
    print("SUCCESS")
    print(json.dumps(output, indent=2))
except Exception as e:
    print(f"Error fetching data: {e}")
