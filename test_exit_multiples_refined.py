from api.index import get_recommended_exit_multiple

def test_exit_multiples_refined():
    test_cases = [
        {"ticker": "AAPL", "sector": "Technology", "industry": "Consumer Electronics", "expected": 15.0, "cat": "Premium"},
        {"ticker": "MSFT", "sector": "Software", "industry": "Infrastructure Software", "expected": 15.0, "cat": "Premium"},
        {"ticker": "KO", "sector": "Consumer Defensive", "industry": "Beverages", "expected": 12.0, "cat": "Defensive"},
        {"ticker": "PG", "sector": "Consumer Staples", "industry": "Household & Personal", "expected": 12.0, "cat": "Defensive"},
        {"ticker": "XOM", "sector": "Energy", "industry": "Oil & Gas Integrated", "expected": 8.0, "cat": "Cyclical"},
        {"ticker": "CVX", "sector": "Oil & Gas", "industry": "Oil & Gas Integrated", "expected": 8.0, "cat": "Cyclical"},
        {"ticker": "TSLA", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers", "expected": 8.0, "cat": "Cyclical"},
        {"ticker": "CAT", "sector": "Industrials", "industry": "Farm & Heavy Construction", "expected": 8.0, "cat": "Cyclical"},
        {"ticker": "JPM", "sector": "Financial Services", "industry": "Banks—Diversified", "expected": 10.0, "cat": "Financials"},
        {"ticker": "O", "sector": "Real Estate", "industry": "REIT—Retail", "expected": 10.0, "cat": "Financials/REITs"},
    ]
    
    print("\n--- Testing REFINED Exit Multiple Mapping ---")
    for case in test_cases:
        res = get_recommended_exit_multiple(case["sector"], case["industry"])
        status = "✅" if res == case["expected"] else "❌"
        print(f"{case['ticker']} ({case['cat']} : {case['sector']}): Got {res}, Expected {case['expected']} {status}")

if __name__ == "__main__":
    test_exit_multiples_refined()
