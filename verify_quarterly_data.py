import sys
import os
import pandas as pd

# Add the project directory to sys.path to import the scraper
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_company_data

def verify_ticker(ticker):
    print(f"\nVerifying {ticker}...")
    data = get_company_data(ticker)
    if not data:
        print(f"Failed to fetch data for {ticker}")
        return
    
    h_data = data.get("historical_data", {})
    years = h_data.get("years", [])
    revenue = h_data.get("revenue", [])
    eps = h_data.get("eps", [])
    fcf = h_data.get("fcf", [])
    shares = h_data.get("shares", [])
    
    print(f"Number of quarters found: {len(years)}")
    if len(years) > 0:
        print(f"Labels: {years}")
        print(f"Revenue sample: {revenue[:2]}")
        print(f"EPS sample: {eps[:2]}")
        
        # Check label format
        for label in years:
            if not (label.startswith('Q') and ' ' in label):
                print(f"WARNING: Unexpected label format: {label}")
                break
        else:
            print("Labels format OK.")
            
        # Check for NaNs (should be filtered out)
        for val in revenue + eps + fcf:
            if pd.isna(val):
                print("ERROR: NaN found in data!")
                break
        else:
            print("No NaNs found in key metrics. OK.")
            
        # Check chronological order (assuming labels like Q1 2023, Q2 2023)
        # Just printing them for manual check is often enough, but let's see if they are unique
        if len(set(years)) == len(years):
            print("Quarters are unique. OK.")
    else:
        print("WARNING: No quarterly data found.")

if __name__ == "__main__":
    verify_ticker("AAPL")
    verify_ticker("MSFT")
    verify_ticker("ADBE")
