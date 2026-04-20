import yfinance as yf
import json

ticker = "HIMS"
stock = yf.Ticker(ticker)

# Try to get the raw module data via a private method if it exists
try:
    # yfinance 0.2.x stores this in the .basic_info or similar, 
    # but for full quoteSummary we might need a direct call.
    # Let's try .get_earnings_trend() which is a known method in some versions
    trend = stock.get_earnings_trend()
    print("Trend found:")
    print(trend)
except:
    print("get_earnings_trend() failed")

# Alternative: check for the trend data in the .info or .stats
# Actually, yfinance 0.2.x has .earnings_estimate row 'yearAgoEps'
est = stock.earnings_estimate
if est is not None:
    print("\nEarnings Estimate:")
    print(est)
