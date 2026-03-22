import yfinance as yf
import json

def debug_ticker(ticker):
    print(f"Fetching data for {ticker}...")
    t = yf.Ticker(ticker)
    info = t.info
    
    important_fields = [
        'currentPrice', 'marketCap', 'trailingEPS', 'trailingPE', 
        'sharesOutstanding', 'operatingMargins', 'profitMargins',
        'longName', 'industry'
    ]
    
    results = {field: info.get(field) for field in important_fields}
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    debug_ticker("ADBE")
