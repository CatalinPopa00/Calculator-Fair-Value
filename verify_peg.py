import requests
import json

def test_peg_refinement(ticker):
    print(f"Testing PEG refinement for {ticker}...")
    try:
        url = f"http://localhost:8000/api/valuation/{ticker}"
        resp = requests.get(url, timeout=30)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            peg = data.get('formula_data', {}).get('peg', {})
            print("PEG Data:")
            print(json.dumps(peg, indent=2))
            
            fair_value = peg.get('fair_value')
            industry_peg = peg.get('industry_peg')
            company_peg = peg.get('current_peg')
            
            if fair_value and industry_peg and company_peg:
                print("Verification: SUCCESS")
            else:
                print("Verification: PARTIAL (Data missing, might be expected for some tickers)")
        else:
            print(f"Failed: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Note: Backend must be running
    test_peg_refinement("AAPL")
