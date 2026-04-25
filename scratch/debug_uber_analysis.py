
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scraper.yahoo import get_yahoo_analysis_normalized
import yfinance as yf
import json

ticker = "UBER"
stock = yf.Ticker(ticker)
info = stock.info

print(f"Fetching Analysis Normalized for {ticker}...")
res = get_yahoo_analysis_normalized(ticker, info)

print("\n--- ANALYSIS TRUTH ---")
print(json.dumps(res, indent=2))
