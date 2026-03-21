import yfinance as yf
for ticker in ["ADBE", "UBER"]:
    stock = yf.Ticker(ticker)
    print(f"\n--- {ticker} EARNINGS ESTIMATE ---")
    try:
        print(stock.earnings_estimate)
    except Exception as e:
        print(e)
