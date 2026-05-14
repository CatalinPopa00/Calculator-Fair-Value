import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.yahoo import get_company_data

data = get_company_data("ADBE")

print("--- ADBE Debt & Cash Info (Platform Model) ---")
print(f"Total Cash: ${data.get('total_cash', 0):,.2f}")
print(f"Total Debt: ${data.get('total_debt', 0):,.2f}")
print(f"Net Debt: ${(data.get('total_debt', 0) - data.get('total_cash', 0)):,.2f}")

try:
    import yfinance as yf
    ticker = yf.Ticker("ADBE")
    info = ticker.info
    print(f"\n--- From yfinance info ---")
    print(f"info['totalCash']: ${info.get('totalCash', 0):,.2f}")
    print(f"info['totalDebt']: ${info.get('totalDebt', 0):,.2f}")
    
    print("\n--- From Balance Sheet (Quarterly) ---")
    q_bs = ticker.quarterly_balance_sheet
    for item in ['Long Term Debt', 'Total Long Term Debt', 'Current Debt', 'Short Term Debt', 'Short Long Term Debt', 'Commercial Paper']:
        if item in q_bs.index:
            print(f"{item}: ${q_bs.loc[item].iloc[0]:,.2f}")
except Exception as e:
    print(e)
