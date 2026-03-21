import sys
import os

# Add the current directory to sys.path to import local modules
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_company_data

def test_profile_enrichment():
    print("--- Testing Profile Enrichment (AAPL) ---")
    
    ticker = "AAPL"
    data = get_company_data(ticker)
    
    if not data:
        print("❌ FAILED: No data returned from get_company_data")
        return

    fields = [
        "business_summary", 
        "insider_ownership", 
        "next_earnings_date", 
        "operating_margins", 
        "net_margin",
        "payout_ratio"
    ]
    
    for f in fields:
        val = data.get(f)
        print(f"{f}: {val}")
        if val is None and f != "payout_ratio": 
            print(f"⚠️ Warning: {f} is None")

    if data.get("business_summary") and data.get("business_summary") != 'Description not available.':
        print("✅ PASSED: Business summary extracted.")
    else:
        print("❌ FAILED: Business summary missing or default.")

    print("\n--- End of Test ---")

if __name__ == "__main__":
    test_profile_enrichment()
