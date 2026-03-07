import yfinance as yf
import json

ticker = "UBER"
stock = yf.Ticker(ticker)

print("--- INFO GROWTH FIELDS ---")
print(f"earningsGrowth: {stock.info.get('earningsGrowth')}")
print(f"revenueGrowth: {stock.info.get('revenueGrowth')}")
print(f"longTermGrowthRate: {stock.info.get('longTermGrowthRate')}")

print("\n--- EARNINGS ESTIMATE ---")
try:
    ef = stock.earnings_estimate
    print(ef)
except Exception as e:
    print(f"Error: {e}")

print("\n--- REVENUE ESTIMATE ---")
try:
    rf = stock.revenue_estimate
    print(rf)
except Exception as e:
    print(f"Error: {e}")
