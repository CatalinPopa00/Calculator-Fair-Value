
import sys
import os
import json

# Add api directory to path
sys.path.append(os.path.abspath('api'))

from scraper.yahoo import get_nasdaq_comprehensive_estimates

def debug_nasdaq():
    ticker = "HIMS"
    print(f"Fetching Nasdaq data for {ticker}...")
    data = get_nasdaq_comprehensive_estimates(ticker, force_refresh=True)
    
    print("\nYearly EPS Forecasts:")
    for row in data.get('yearly_eps', []):
        print(f"  {row.get('fiscalYearEnd') or row.get('fiscalEnd')}: {row.get('consensusEPSForecast')}")
        
    print("\nQuarterly EPS Forecasts:")
    for row in data.get('quarterly_eps', []):
        print(f"  {row.get('fiscalQuarterEnd')}: {row.get('consensusEPSForecast')}")

if __name__ == "__main__":
    debug_nasdaq()
