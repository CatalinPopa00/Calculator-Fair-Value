
import yfinance as yf
ticker = "UBER"
stock = yf.Ticker(ticker)
print("--- REVENUE ESTIMATE ---")
print(stock.revenue_estimate)
print("\n--- EARNINGS ESTIMATE ---")
print(stock.earnings_estimate)
