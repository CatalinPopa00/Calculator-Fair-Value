
import yfinance as yf

tickers = ["PFE", "ABBV"]
for t in tickers:
    stock = yf.Ticker(t)
    info = stock.info
    print(f"\n--- {t} ---")
    print(f"revenueGrowth: {info.get('revenueGrowth')}")
    print(f"earningsGrowth: {info.get('earningsGrowth')}")
    print(f"earningsQuarterlyGrowth: {info.get('earningsQuarterlyGrowth')}")
