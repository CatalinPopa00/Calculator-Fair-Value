import yfinance as yf
import json

ticker = "NKE"
stock = yf.Ticker(ticker)
info = stock.info

print("--- Nike Info Data ---")
print(f"Trailing EPS: {info.get('trailingEps')}")
print(f"Forward EPS: {info.get('forwardEps')}")
print(f"Earnings Growth: {info.get('earningsGrowth')}")
print(f"Revenue Growth: {info.get('revenueGrowth')}")
print(f"PEG Ratio: {info.get('pegRatio')}")

# Try to get growth estimates manually
try:
    ge = stock.growth_estimates
    print("\n--- Growth Estimates ---")
    print(ge)
except:
    print("\nGrowth Estimates not available")
