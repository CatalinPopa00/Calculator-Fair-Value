
import yfinance as yf
ticker = "AAPL"
stock = yf.Ticker(ticker)
eh = stock.earnings_history
if eh is not None and not eh.empty:
    print("Earnings History (All):")
    print(eh.sort_index(ascending=False)[['epsActual', 'epsEstimate']])
