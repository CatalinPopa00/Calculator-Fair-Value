import yfinance as yf
import json

def test_yf_batch():
    tickers = ["LLY", "JNJ", "PFE"]
    print(f"Testing yfinance batch for: {tickers}")
    try:
        # Use yf.Tickers for batch download
        data = yf.Tickers(" ".join(tickers))
        for t in tickers:
            info = data.tickers[t].info
            print(f"Ticker: {t}, Price: {info.get('regularMarketPrice') or info.get('currentPrice')}, PE: {info.get('trailingPE')}")
    except Exception as e:
        print(f"yfinance Error: {e}")

if __name__ == "__main__":
    test_yf_batch()
