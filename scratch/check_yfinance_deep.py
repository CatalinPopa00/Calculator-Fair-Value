import yfinance as yf
import json

ticker = "HIMS"
stock = yf.Ticker(ticker)

# Try accessing the internal quote_summary dictionary
try:
    # Some versions have it here
    qs = stock.quote_summary
    print("Found quote_summary")
    trend = qs.get('earningsTrend', {}).get('trend', [])
    for t in trend:
        print(f"Period {t.get('period')}: Year Ago {t.get('earningsEstimate', {}).get('yearAgoEps')}")
except:
    print("stock.quote_summary missing")

# Try another way: stock.news? No.
# Try stock.get_earnings_history()
try:
    eh = stock.get_earnings_history()
    print("\nEarnings History:")
    print(eh)
except:
    print("get_earnings_history() failed")
