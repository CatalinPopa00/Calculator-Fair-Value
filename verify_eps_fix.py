import yfinance as yf
import statistics
import concurrent.futures

def get_nasdaq_earnings_growth(ticker: str, trailing_eps: float) -> float:
    # Simulating Nasdaq failure to test YF estimates fallback
    return None

def verify_growth_logic(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_growth = executor.submit(get_nasdaq_earnings_growth, ticker_symbol, info.get('trailingEps'))
        future_est = executor.submit(lambda: stock.earnings_estimate)

        trailing_eps = info.get('trailingEps') or info.get('epsTrailingTwelveMonths')
        forward_eps = info.get('forwardEps')
        
        # Logic from updated yahoo.py
        eps_growth = future_growth.result(timeout=5)
        
        source = "Nasdaq" if eps_growth else None
        
        if eps_growth is None:
            try:
                ef = future_est.result(timeout=2)
                if ef is not None and not ef.empty and '+1y' in ef.index:
                    growth_val = ef.loc['+1y'].get('growth')
                    if growth_val is not None:
                        eps_growth = float(growth_val)
                        source = "YF Earnings Estimate (+1y)"
            except Exception as e:
                print(f"Error in EF: {e}")

        if eps_growth is None:
            eps_growth = info.get('earningsGrowth')
            source = "YF Info earningsGrowth"
            if not eps_growth and forward_eps and trailing_eps and trailing_eps > 0:
                eps_growth = (forward_eps - trailing_eps) / trailing_eps
                source = "YF Trailing/Forward Calc"
            elif not eps_growth:
                eps_growth = info.get('revenueGrowth', 0.05)
                source = "YF Info revenueGrowth (Fallback)"

    print(f"Ticker: {ticker_symbol}")
    print(f"Resulting EPS Growth: {eps_growth}")
    print(f"Source: {source}")
    print(f"Trailing Info earningsGrowth: {info.get('earningsGrowth')}")

if __name__ == "__main__":
    verify_growth_logic("UBER")
