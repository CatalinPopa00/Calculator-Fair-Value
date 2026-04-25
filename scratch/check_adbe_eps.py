import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.yahoo import get_analyst_data

ticker = "ADBE"
print(f"Fetching analyst data for {ticker}...")
try:
    analyst = get_analyst_data(ticker)
    eps_est = analyst.get("eps_estimates", [])
    print("\nEPS Estimates:")
    for est in eps_est:
        print(f"Period: {est.get('period')}, Avg: {est.get('avg')}, Status: {est.get('status')}")
    
except Exception as e:
    print(f"Error: {e}")
