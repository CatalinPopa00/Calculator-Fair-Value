import sys
import os
# Add the current directory to sys.path
sys.path.append(os.getcwd())

from scraper.yahoo import get_analyst_data, get_company_data
import yfinance as yf
import json

ticker = 'AAPL'
company_data = get_company_data(ticker, fast_mode=True)
result = get_analyst_data(ticker, historical_data=company_data.get('historical_data'))

print(json.dumps({
    "eps_estimates": result.get('eps_estimates'),
    "rev_estimates": result.get('rev_estimates'),
    "historical_last": {
        "year": company_data.get('historical_data', {}).get('years', [])[-1],
        "eps": company_data.get('historical_data', {}).get('eps', [])[-1],
        "rev": company_data.get('historical_data', {}).get('revenue', [])[-1]
    }
}, indent=2))
