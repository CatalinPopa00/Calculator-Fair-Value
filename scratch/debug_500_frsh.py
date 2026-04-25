import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.yahoo import get_company_data, get_analyst_data

ticker = "FRSH"
print(f"Testing {ticker}...")
try:
    data = get_company_data(ticker)
    print("Company Data Success")
    # print(data)
    
    analyst = get_analyst_data(ticker)
    print("Analyst Data Success")
    # print(analyst)
    
except Exception as e:
    import traceback
    print(f"FAILED for {ticker}: {e}")
    traceback.print_exc()
