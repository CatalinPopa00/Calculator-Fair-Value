import yfinance as yf
import json

def explore_ticker(symbol):
    print(f"Exploring {symbol}...")
    t = yf.Ticker(symbol)
    
    # Check all attributes
    attrs = dir(t)
    potential = [a for a in attrs if 'peer' in a.lower() or 'comp' in a.lower() or 'recommend' in a.lower() or 'watch' in a.lower()]
    print(f"Potential attributes: {potential}")
    
    # Check info keys
    info = t.info
    info_keys = list(info.keys())
    potential_info = [k for k in info_keys if 'peer' in k.lower() or 'comp' in k.lower() or 'recommend' in k.lower()]
    print(f"Potential info keys: {potential_info}")
    
    # Check specific attributes that might hold data
    try:
        print("\nRecommendations summary:")
        print(t.recommendations_summary)
    except:
        pass

    try:
        # Some versions/tools use 'news' to find related tickers
        print("\nNews tickers:")
        for n in t.news:
            print(n.get('relatedTickers'))
    except:
        pass

if __name__ == "__main__":
    explore_ticker("AAPL")
