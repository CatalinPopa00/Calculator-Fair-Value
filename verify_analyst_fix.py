import sys
import os
import datetime

# Add the project root to sys.path
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_analyst_data
import json

def test_ticker(ticker):
    print(f"\n--- Testing Ticker: {ticker} ---")
    try:
        data = get_analyst_data(ticker)
        if "error" in data:
            print(f"Error for {ticker}: {data['error']}")
            return False
        
        eps_est = data.get("eps_estimates", [])
        rev_est = data.get("rev_estimates", [])
        
        print(f"Found {len(eps_est)} EPS estimates")
        print(f"Found {len(rev_est)} Revenue estimates")
        
        # Check labels
        labels = [e['period'] for e in eps_est]
        print(f"Labels: {labels}")
        
        # Check FY labels
        fy_labels = [l for l in labels if "FY" in l]
        q_labels = [l for l in labels if "Q" in l]
        
        if not fy_labels:
            print(f"FAILED: No FY labels found for {ticker}")
        if not q_labels:
            print(f"WARNING: No Q labels found for {ticker} (might be expected if no quarterly estimates)")
            
        # Specific check for NVDA current FY (should be 2027 if today is April 2026)
        if ticker == "NVDA":
            if any("2026" in l and "Q" in l for l in labels):
                print(f"FAILED: Found 2026 quarters for NVDA, expected 2027.")
            elif any("2027" in l for l in labels):
                print(f"SUCCESS: Found 2027 labels for NVDA.")
            else:
                print(f"WARNING: No 2027 labels found for NVDA.")

        return True
    except Exception as e:
        print(f"Exception for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    tickers = ["NVDA", "ADBE", "MSFT"]
    results = [test_ticker(t) for t in tickers]
    
    if all(results):
        print("\nOVERALL STATUS: SUCCESS")
        sys.exit(0)
    else:
        print("\nOVERALL STATUS: FAILED")
        sys.exit(1)
