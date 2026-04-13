import sys, os
sys.path.insert(0, os.getcwd())
from api.scraper.yahoo import get_analyst_data
import yfinance as yf

stock = yf.Ticker("ADBE")
info = stock.info

result = get_analyst_data(stock, "ADBE", info)

print("=== EPS ESTIMATES ===")
for e in result.get("eps_estimates", []):
    print(f"  {e.get('period'):15s}  avg={e.get('avg'):10.2f}  growth={e.get('growth')}")

print("\n=== REV ESTIMATES ===")
for r in result.get("rev_estimates", []):
    avg = r.get('avg')
    if avg:
        print(f"  {r.get('period'):15s}  avg={avg/1e9:7.2f}B  growth={r.get('growth')}")

print(f"\n=== GROWTH ===")
print(f"  eps_5yr_growth: {result.get('eps_5yr_growth')}")
print(f"  eps_growth_5y_consensus: {result.get('eps_growth_5y_consensus')}")
