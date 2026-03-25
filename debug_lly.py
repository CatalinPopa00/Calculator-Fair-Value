
import yfinance as yf
import json

ticker = "LLY"
stock = yf.Ticker(ticker)
info = stock.info

print(f"--- yfinance info for {ticker} ---")
growth_keys = [k for k in info.keys() if 'growth' in k.lower()]
print(f"Growth keys found: {growth_keys}")

for k in growth_keys:
    print(f"{k}: {info.get(k)}")

print(f"\nTarget keys:")
print(f"revenueGrowth: {info.get('revenueGrowth')}")
print(f"earningsGrowth: {info.get('earningsGrowth')}")
print(f"earningsQuarterlyGrowth: {info.get('earningsQuarterlyGrowth')}")
