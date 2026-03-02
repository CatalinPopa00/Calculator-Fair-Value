import yfinance as yf
stock = yf.Ticker("AAPL")
info = stock.info

print("earningsGrowth", info.get("earningsGrowth"))
print("revenueGrowth", info.get("revenueGrowth"))
print("pegRatio", info.get("pegRatio"))
print("trailingPE", info.get("trailingPE"))
print("forwardPE", info.get("forwardPE"))

# Looking for next year growth
