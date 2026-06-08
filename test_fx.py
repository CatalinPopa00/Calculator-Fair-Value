import yfinance as yf
ticker = yf.Ticker('RHM.DE')
info = ticker.info
print("currency", info.get("currency"))
print("financialCurrency", info.get("financialCurrency"))
print("currentPrice", info.get("currentPrice"))
print("trailingEps", info.get("trailingEps"))
