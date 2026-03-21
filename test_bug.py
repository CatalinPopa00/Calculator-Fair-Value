import sys
import json
sys.path.insert(0, 'backend')
from scraper.yahoo import get_analyst_data
import yfinance as yf

# Let's find out what ticker this is. PT $26.50, Hold, Score 2.68. Probably PLTR for an old cache?
print("=== TESTING PLTR ===")
try:
    data = get_analyst_data('PLTR')
    print("Recommendations:", json.dumps(data.get('recommendation', {}), indent=2))
    print("EPS:", json.dumps(data.get('eps_estimates', []), indent=2))
    print("REV:", json.dumps(data.get('rev_estimates', []), indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()

print("=== YFINANCE RAW (PLTR) ===")
try:
    stock = yf.Ticker('PLTR')
    print("rec_df:")
    print(stock.recommendations_summary)
except Exception as e:
    print("err:", e)
