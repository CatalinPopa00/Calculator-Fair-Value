import yfinance as yf
import requests
import json
import urllib.request
import os
import pandas as pd
from api.scraper.yahoo import get_company_data

def get_random_agent():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def test_nasdaq(ticker):
    print(f"\n--- Testing Nasdaq for {ticker} ---")
    try:
        url = f'https://api.nasdaq.com/api/analyst/{ticker.upper()}/earnings-forecast'
        req = urllib.request.Request(url, headers={'User-Agent': get_random_agent()})
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read()
            # print(f"Raw: {raw_data[:200]}")
            data = json.loads(raw_data)
            rows = data.get('data', {}).get('yearlyForecast', {}).get('rows', [])
            print(f"Nasdaq Rows: {len(rows)}")
            if rows:
                print(f"First row: {rows[0]}")
    except Exception as e:
        print(f"Nasdaq Error: {e}")

def test_yahoo(ticker):
    print(f"\n--- Testing Yahoo for {ticker} ---")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        print(f"Info Name: {info.get('shortName')}")
        
        # Test financial data directly without futures for diagnosis
        fin = stock.financials
        data = get_company_data(ticker)
        print(f"Yahoo Name: {data.get('name')}")
        print(f"FCF: {data.get('fcf')}")
        print(f"Financials empty? {data.get('financials_empty', 'Unknown')}")
        print(f"Found 'EBIT'? {data.get('ebit_margin') is not None}")
        print(f"Found 'Total Revenue'? {data.get('revenue') is not None}")
        print(f"Cashflow empty? {data.get('cashflow_empty', 'Unknown')}")
        cf = stock.cashflow # Re-initialize cf for the original check if needed, or remove
        if cf is not None and not cf.empty:
            print(f"Found 'Free Cash Flow'? {'Free Cash Flow' in cf.index}")
            
    except Exception as e:
        print(f"Yahoo Error: {e}")

if __name__ == "__main__":
    for t in ["V"]:
        test_nasdaq(t)
        test_yahoo(t)
