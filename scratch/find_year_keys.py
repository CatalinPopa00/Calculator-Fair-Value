import yfinance as yf

ticker = "HIMS"
stock = yf.Ticker(ticker)
info = stock.info

for k, v in info.items():
    if "Year" in k or "Ago" in k or "Prev" in k or "Last" in k:
        print(f"{k}: {v}")
