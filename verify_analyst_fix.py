import sys
import os

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
        
        missing_code_eps = [e for e in eps_est if "period_code" not in e]
        missing_code_rev = [r for r in rev_est if "period_code" not in r]
        
        if missing_code_eps:
            print(f"FAILED: {len(missing_code_eps)} EPS estimates missing 'period_code'")
        if missing_code_rev:
            print(f"FAILED: {len(missing_code_rev)} Revenue estimates missing 'period_code'")
            
        if not missing_code_eps and not missing_code_rev:
            print(f"SUCCESS: All estimates have 'period_code' for {ticker}")
            # print(json.dumps(eps_est[:2], indent=2))
            return True
        return False
    except Exception as e:
        print(f"Exception for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    tickers = ["ADBE", "AAPL", "MSFT"]
    results = [test_ticker(t) for t in tickers]
    
    if all(results):
        print("\nOVERALL STATUS: SUCCESS")
        sys.exit(0)
    else:
        print("\nOVERALL STATUS: FAILED")
        sys.exit(1)
