import yfinance as yf
stock = yf.Ticker("SOFI")
print("Earnings Estimate:")
print(stock.earnings_estimate)
print("\nInfo Keys (partial):")
info = stock.info
print({k: info.get(k) for k in ['earningsGrowth', 'revenueGrowth', 'longTermConsensusGrowth', 'growthRate'] if k in info})
