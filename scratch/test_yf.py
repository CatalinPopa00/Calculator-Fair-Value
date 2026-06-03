import yfinance as yf
import json

def test():
    ticker = yf.Ticker("AAPL")
    it = ticker.insider_transactions
    if it is not None:
        print("Columns: ", it.columns.tolist())
        print(it.head().to_dict(orient="records"))

if __name__ == "__main__":
    test()
