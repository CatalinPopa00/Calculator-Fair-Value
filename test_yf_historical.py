import yfinance as yf
import pandas as pd

def test_historical(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    
    # Financials
    fin = stock.financials
    cf = stock.cashflow
    
    print("--- Financials Index ---")
    print(fin.index.tolist())
    
    print("\n--- Cashflow Index ---")
    print(cf.index.tolist())
    
    # Extract data
    years = [col.year for col in fin.columns]
    
    revenue = []
    if 'Total Revenue' in fin.index:
        revenue = fin.loc['Total Revenue'].tolist()
        
    eps = []
    if 'Diluted EPS' in fin.index:
        eps = fin.loc['Diluted EPS'].tolist()
    elif 'Basic EPS' in fin.index:
        eps = fin.loc['Basic EPS'].tolist()
        
    fcf = []
    if 'Free Cash Flow' in cf.index:
        fcf = cf.loc['Free Cash Flow'].tolist()
        
    shares = []
    # Try multiple share keys
    share_keys = ['Basic Average Shares', 'Diluted Average Shares', 'Ordinary Shares Number']
    for key in share_keys:
        if key in fin.index:
            shares = fin.loc[key].tolist()
            break
        elif key in cf.index:
            shares = cf.loc[key].tolist()
            break

    print(f"\nYears: {years}")
    print(f"Revenue: {revenue}")
    print(f"EPS: {eps}")
    print(f"FCF: {fcf}")
    print(f"Shares: {shares}")

if __name__ == "__main__":
    test_historical("AAPL")
