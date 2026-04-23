import yfinance as yf
import json

def test_meta_info(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    print(f"--- Meta Info for {ticker} ---")
    
    keys_of_interest = [
        'epsCurrentYear', 'epsForward', 'forwardEps', 'trailingEps', 
        'epsGrowth', 'earningsGrowth', 'revenueGrowth'
    ]
    
    for k in keys_of_interest:
        print(f"{k}: {info.get(k)}")
    
    # Save full info for deep inspection
    with open(f"{ticker}_full_info.json", "w") as f:
        json.dump(info, f, indent=2)

if __name__ == "__main__":
    test_meta_info("META")
