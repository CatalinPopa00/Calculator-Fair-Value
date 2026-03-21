import yfinance as yf
import json

try:
    stock = yf.Ticker("AAPL")
    info = stock.info
    
    # Dump info to file
    with open("aapl_info.json", "w") as f:
        json.dump(info, f, indent=4)
        print("Successfully wrote info to aapl_info.json")
except Exception as e:
    print(f"Error: {e}")
