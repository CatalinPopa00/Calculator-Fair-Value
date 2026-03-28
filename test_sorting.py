from api.scraper.yahoo import get_company_data
import json

def test_data_order():
    ticker = "AAPL"
    print(f"Testing scraper for {ticker}...")
    try:
        data = get_company_data(ticker)
        if not data:
            print("Failed to get data.")
            return

        print("\n--- Historical Data (Charts) ---")
        years = data.get("historical_data", {}).get("years", [])
        print(f"Years: {years}")
        
        # Check ascending order
        hist_years = [y for y in years if "Est" not in str(y)]
        if hist_years == sorted(hist_years):
            print("✅ Historical years are in ascending order.")
        else:
            print("❌ Historical years are NOT in ascending order.")

        # Check projections
        est_years = [y for y in years if "Est" in str(y)]
        print(f"Estimates: {est_years}")
        if est_years:
            last_hist = int(hist_years[-1])
            first_est = int(est_years[0].split()[0])
            if first_est > last_hist:
                print(f"✅ Projections start correctly after {last_hist}.")
            else:
                print(f"❌ Projections overlap or precede historical data: {first_est} <= {last_hist}")

        print("\n--- Historical Anchors (Table) ---")
        anchors = data.get("historical_anchors", [])
        anchor_years = [a["year"] for a in anchors]
        print(f"Anchor Years: {anchor_years}")
        if anchor_years == sorted(anchor_years, reverse=True):
            print("✅ Anchor years are in descending order.")
        else:
            print("❌ Anchor years are NOT in descending order.")

    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    test_data_order()
