import yfinance as yf
import pandas as pd
from api.scraper.yahoo import find_idx, find_nearest_col

def debug_meta_eps():
    ticker = "META"
    stock = yf.Ticker(ticker)
    financials = stock.financials
    
    print(f"--- Debugging {ticker} Financials ---")
    if financials is not None and not financials.empty:
        print("\n[Financials Columns]")
        print(financials.columns)
        
        # Check Diluted EPS
        eps_idx = find_idx(financials, 'Diluted EPS')
        print(f"\n[Diluted EPS Index]: {eps_idx}")
        if eps_idx:
            print(financials.loc[eps_idx])
            
        # Check Revenue
        rev_idx = find_idx(financials, 'Total Revenue')
        print(f"\n[Total Revenue Index]: {rev_idx}")
        if rev_idx:
            print(financials.loc[rev_idx])
    else:
        print("Financials empty!")

if __name__ == "__main__":
    debug_meta_eps()
