
import requests
import json

def test_local_valuation():
    ticker = "UBER"
    url = f"http://127.0.0.1:8000/api/valuation/{ticker}"
    print(f"Testing local API: {url}")
    try:
        # Increase timeout because scraping is slow
        response = requests.get(url, timeout=15)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            # Check eps_growth in formula_data
            pl_growth = data.get("formula_data", {}).get("peter_lynch", {}).get("eps_growth_estimated")
            peg_growth = data.get("formula_data", {}).get("peg", {}).get("eps_growth_estimated")
            print(f"Peter Lynch Growth: {pl_growth}")
            print(f"PEG Growth: {peg_growth}")
            print(f"Label: {data.get('formula_data', {}).get('peter_lynch', {}).get('eps_growth_period')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    test_local_valuation()
