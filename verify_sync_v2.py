import requests
import json

def verify_sync(ticker):
    url = f"http://localhost:3000/api/valuation/{ticker}?refresh=true"
    print(f"Checking {ticker} at {url}...")
    try:
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        data = res.json()
        
        formula_data = data.get("formula_data", {})
        dcf = formula_data.get("dcf", {})
        pv = formula_data.get("peter_lynch", {})
        peg = formula_data.get("peg", {})
        
        dcf_growth = dcf.get("eps_growth_applied")
        pv_growth = pv.get("eps_growth")
        peg_growth = peg.get("eps_growth")
        
        print(f"--- Results for {ticker} ---")
        print(f"DCF Growth:   {dcf_growth}")
        print(f"Lynch Growth: {pv_growth}")
        print(f"PEG Growth:   {peg_growth}")
        
        if dcf_growth == pv_growth == peg_growth:
            print("✅ SUCCESS: Growth rates are synchronized.")
        else:
            print("❌ FAILURE: Growth rates are inconsistent.")
            
        # Check conservative cap (if negative)
        if dcf_growth is not None and dcf_growth < 0:
            eff_pe = pv.get("effective_pe_multiple")
            print(f"Negative Growth Detected. Effective PE: {eff_pe}")
            if eff_pe and eff_pe <= 12.0:
                print("✅ SUCCESS: Conservative cap applied.")
            else:
                print("❌ FAILURE: Conservative cap NOT applied.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_sync("NVO")
