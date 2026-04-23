
import yfinance as yf
ticker = "UBER"
s = yf.Ticker(ticker)
print("--- EARNINGS MODULE ---")
print(s.earnings)
print("\n--- QUARTERLY EARNINGS ---")
print(s.quarterly_earnings)
