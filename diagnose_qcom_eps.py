import sys
import os
import json
from datetime import datetime

# Add root and api to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'api'))

from api.scraper.yahoo import get_analyst_data, get_nasdaq_comprehensive_estimates
import yfinance as yf

ticker = "QCOM"
stock = yf.Ticker(ticker)
info = stock.info

print(f"--- QCOM Analyst Data Audit ---")
data = get_nasdaq_comprehensive_estimates(ticker)
print(json.dumps(data, indent=2))

analyst = get_analyst_data(stock, ticker, info)
print("\n--- Processed Analyst Data ---")
print(json.dumps(analyst.get('eps_estimates'), indent=2))
