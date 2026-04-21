
import sys
import os
import re

# Add the project root to sys.path
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value')

from api.scraper.yahoo import get_company_data, get_analyst_data
import yfinance as yf

ticker = 'AAPL'
print(f"--- Diagnosing {ticker} Growth ---")
cd = get_company_data(ticker, fast_mode=True)
hist_data = cd.get('historical_data')
print("Historical Data Years:", hist_data['years'])
print("Historical Data EPS:", hist_data['eps'])

# Simulate the guts of get_analyst_data
info = cd.get('info')
stock = yf.Ticker(ticker)

try:
    analyst = get_analyst_data(stock, ticker, info, historical_data=hist_data)
    eps_est = analyst.get('eps_estimates', [])
    for e in eps_est:
        if 'FY' in e['period']:
            print(f"Period: {e['period']}, Avg: {e.get('avg')}, Growth: {e.get('growth')}")
except Exception as e:
    import traceback
    traceback.print_exc()
