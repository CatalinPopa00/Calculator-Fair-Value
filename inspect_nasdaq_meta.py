import sys
import os
import json
import urllib.request

# Add api directory to path
sys.path.append(os.path.join(os.getcwd(), 'api'))

from scraper.yahoo import get_nasdaq_comprehensive_estimates

def inspect_nasdaq_meta():
    print("--- INSPECTING NASDAQ RAW DATA FOR META ---")
    data = get_nasdaq_comprehensive_estimates('META')
    print("Yearly EPS Rows:")
    for i, row in enumerate(data.get('yearly_eps', [])):
        print(f"Row {i}: {row}")
    
    print("\nYearly Rev Rows:")
    for i, row in enumerate(data.get('yearly_rev', [])):
        print(f"Row {i}: {row}")

if __name__ == "__main__":
    inspect_nasdaq_meta()
