import yfinance as yf
import json

def debug_visa():
    ticker = yf.Ticker("V")
    info = ticker.info
    print(f"Ticker: {ticker.ticker}")
    print(f"Operating Margins (info): {info.get('operatingMargins')}")
    
    financials = ticker.financials
    if financials is not None and not financials.empty:
        print("\nFinancials Index:")
        print(financials.index.tolist())
        
        for key in ['EBIT', 'Operating Income', 'Total Revenue', 'Net Income']:
            if key in financials.index:
                print(f"{key} (latest): {financials.loc[key].iloc[0]}")
            else:
                # Try case insensitive search
                found = [idx for idx in financials.index if key.lower() in idx.lower()]
                if found:
                    print(f"Found similar for {key}: {found} -> {financials.loc[found[0]].iloc[0]}")

if __name__ == "__main__":
    debug_visa()
