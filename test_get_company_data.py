import sys
sys.path.append('.')
from scraper.yahoo import get_company_data

def test_ticker(ticker):
    print(f"--- {ticker} ---")
    data = get_company_data(ticker, fast_mode=False)
    print(f"current_price: {data.get('current_price')}")
    print(f"trailing_eps: {data.get('trailing_eps')}")
    print(f"adjusted_eps: {data.get('adjusted_eps')}")

test_ticker('RHM.DE')
