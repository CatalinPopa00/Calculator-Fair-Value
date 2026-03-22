import yfinance as yf
import json

def debug_ticker_multi(ticker):
    print(f"Fetching data for {ticker}...")
    t = yf.Ticker(ticker)
    
    # Try different ways to get price
    info_price = t.info.get('currentPrice')
    history = t.history(period='1d')
    hist_price = history['Close'].iloc[-1] if not history.empty else None
    
    results = {
        "ticker": ticker,
        "info_price": info_price,
        "hist_price": hist_price,
        "market_cap": t.info.get('marketCap'),
        "long_name": t.info.get('longName')
    }
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    debug_ticker_multi("ADBE")
    debug_ticker_multi("NVDA")
    debug_ticker_multi("AAPL")
