
import sys
import os
import traceback
# Add the project root to sys.path
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_company_data
import json

ticker = "ADBE"
print(f"Scraping {ticker} with full traceback...")
try:
    data = get_company_data(ticker)
    print("Success!")
except Exception as e:
    print("\n--- ERROR ---")
    print(str(e))
    traceback.print_exc()

