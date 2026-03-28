import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_company_data

def test_visa():
    ticker = "V"
    print(f"Testing {ticker} data extraction...")
    # get_company_data is NOT async
    data = get_company_data(ticker)
    
    if data:
        print("Success!")
        print(f"Name: {data.get('name')}")
        print(f"Price: {data.get('current_price')}")
        print(f"Trailing EPS: {data.get('trailing_eps')}")
        print(f"Sector: {data.get('sector')}")
        print(f"Industry: {data.get('industry')}")
        print(f"PE Ratio: {data.get('pe_ratio')}")
        print(f"EPS Growth 5Y: {data.get('eps_growth_5y')}")
        print(f"FCF: {data.get('fcf')}")
    else:
        print("Failed to fetch data.")

if __name__ == "__main__":
    test_visa()
