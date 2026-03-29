import yfinance as yf
ticker = "SMCI"
t = yf.Ticker(ticker)
info = t.info
print("\n--- YAML INFO ---")
print(f"revenueGrowth: {info.get('revenueGrowth')}")
print(f"revenueQuarterlyGrowth: {info.get('revenueQuarterlyGrowth')}")
print(f"earningsGrowth: {info.get('earningsGrowth')}")
print(f"earningsQuarterlyGrowth: {info.get('earningsQuarterlyGrowth')}")

print("\n--- ESTIMATES ---")
try:
    print("Revenue Estimate:\n", t.revenue_estimate)
except:
    print("No revenue_estimate")

try:
    print("Earnings Estimate:\n", t.earnings_estimate)
except:
    print("No earnings_estimate")
