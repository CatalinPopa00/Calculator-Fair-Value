import requests
import json

def test_synthesis(ticker):
    url = f"http://localhost:8000/api/valuation/{ticker}"
    print(f"Testing {ticker}...")
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            synthesis = data.get("company_overview_synthesis")
            print(f"Synthesis for {ticker}:")
            print(synthesis)
            if synthesis:
                if "Sinteză indisponibilă" in synthesis or "este o entitate majoră în sectorul" in synthesis:
                    print("Result: FALLBACK USED")
                else:
                    print("Result: KNOWLEDGE BASE USED")
            else:
                print("Result: ERROR - NO SYNTHESIS FIELD")
        else:
            print(f"Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_synthesis("AAPL")
    print("-" * 50)
    test_synthesis("ASML")
