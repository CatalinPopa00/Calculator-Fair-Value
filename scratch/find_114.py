import yfinance as yf

ticker = "HIMS"
stock = yf.Ticker(ticker)
info = stock.info

for k, v in info.items():
    if v is not None and isinstance(v, (int, float)):
        if 1.0 < v < 1.3:
            print(f"{k}: {v}")
