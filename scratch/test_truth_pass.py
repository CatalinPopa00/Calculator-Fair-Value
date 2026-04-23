import sys
import os
sys.path.append(os.getcwd())
from scraper.yahoo import get_company_data
import json

def test_truth_pass(ticker):
    print(f"Testing Forensic Truth Pass for {ticker}...")
    data = get_company_data(ticker)
    
    if "error" in data:
        print(f"Error: {data['error']}")
        return

    print(f"Ticker: {data['ticker']}")
    
    # Check historical_data["eps"] - last anchor
    if "historical_data" in data and data["historical_data"]["eps"]:
        last_eps = data["historical_data"]["eps"][-3] if len(data["historical_data"]["eps"]) >= 3 else "N/A"
        # Wait, the projections are appended to historical_data["eps"]
        # So [-3] is the last reported anchor (2025), [-2] is 2026 Est, [-1] is 2027 Est.
        print(f"Anchor EPS (2025?): {data['historical_data']['eps'][-3]}")
        print(f"Current Year Est (2026?): {data['historical_data']['eps'][-2]}")
        print(f"Next Year Est (2027?): {data['historical_data']['eps'][-1]}")

    # Check trends
    if "historical_trends" in data:
        print("\nHistorical Trends (Last 3 entries):")
        for tr in data["historical_trends"][-3:]:
            print(f"Year: {tr['year']}, EPS: {tr['eps']}")

if __name__ == "__main__":
    test_truth_pass("META")
