import yfinance as yf

stock = yf.Ticker("ADBE")
info = stock.info

print("=== PRICE SOURCES ===")
for key in ['regularMarketPrice', 'currentPrice', 'previousClose', 'regularMarketPreviousClose', 'open', 'regularMarketOpen', 'dayHigh', 'dayLow', 'fiftyTwoWeekHigh', 'fiftyTwoWeekLow', 'bid', 'ask']:
    val = info.get(key)
    if val:
        print(f"  {key}: ${val}")

print(f"\n=== KEY METRICS ===")
print(f"  trailingPE: {info.get('trailingPE')}")
print(f"  trailingEps: {info.get('trailingEps')}")
print(f"  marketCap: ${info.get('marketCap', 0)/1e9:.2f}B")
print(f"  sharesOutstanding: {info.get('sharesOutstanding', 0)/1e6:.1f}M")

# Check fast_info for more reliable price
try:
    fi = stock.fast_info
    print(f"\n=== FAST INFO ===")
    print(f"  last_price: ${fi.get('lastPrice', 'N/A')}")
    print(f"  previous_close: ${fi.get('previousClose', 'N/A')}")
    print(f"  market_cap: ${fi.get('marketCap', 0)/1e9:.2f}B")
except Exception as e:
    print(f"fast_info error: {e}")

# Check history for most recent close
hist = stock.history(period="5d")
if not hist.empty:
    print(f"\n=== RECENT HISTORY ===")
    for idx, row in hist.iterrows():
        print(f"  {idx.strftime('%Y-%m-%d')}: Close=${row['Close']:.2f}")
