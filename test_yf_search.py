import yfinance as yf
import json

def test_yf_search(ticker):
    print(f"Testing yf.Search for {ticker}...")
    try:
        s = yf.Search(ticker)
        print("Quotes:")
        for q in s.quotes:
            print(f"  {q.get('symbol')} - {q.get('shortname')}")
        
        print("\nNews related tickers:")
        tickers = set()
        for n in s.news:
            related = n.get('relatedTickers')
            if related:
                for t in related:
                    if t != ticker:
                        tickers.add(t)
        print(list(tickers))
        return list(tickers)
    except Exception as e:
        print(f"Error: {e}")
    return []

if __name__ == "__main__":
    test_yf_search("INTU")
    print("-" * 20)
    test_yf_search("AAPL")
