import yfinance as yf
from api.scraper.yahoo import get_company_data, get_analyst_data
import json

def verify_fx():
    ticker = "NVO"
    print(f"--- Verifying FX for {ticker} ---")
    
    # Get raw info to see currencies
    stock = yf.Ticker(ticker)
    info = stock.info
    fin_curr = info.get('financialCurrency')
    price_curr = info.get('currency')
    print(f"Financial Currency: {fin_curr}")
    print(f"Price Currency: {price_curr}")
    
    # Get normalized data
    data = get_company_data(ticker)
    
    print("\nAbsolute Values (Normalized to USD):")
    print(f"Current Price: {data['current_price']} {price_curr}")
    print(f"Trailing EPS: {data['trailing_eps']}")
    print(f"Revenue: {data['revenue']}")
    print(f"FCF: {data['fcf']}")
    print(f"Total Cash: {data['total_cash']}")
    print(f"Total Debt: {data['total_debt']}")
    
    # Check if growth rates are still percentages (between 0 and 1 usually, or realistic)
    print(f"\nGrowth Rates (Ratios - should NOT be converted):")
    print(f"EPS Growth: {data['eps_growth']}")
    
    # Analyst Data
    print(f"\n--- Analyst Data for {ticker} ---")
    analyst = get_analyst_data(ticker)
    eps_est = analyst.get('eps_estimates', [])
    if eps_est:
        print(f"First EPS Estimate: {eps_est[0]['avg']}")
    
    rev_est = analyst.get('rev_estimates', [])
    if rev_est:
        print(f"First Revenue Estimate: {rev_est[0]['avg']}")

if __name__ == "__main__":
    verify_fx()
