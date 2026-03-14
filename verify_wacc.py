import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.curdir))

from api.index import get_valuation

def verify():
    ticker = "AAPL"
    print(f"--- Verifying Ticker: {ticker} ---")
    try:
        data = get_valuation(ticker)
        
        print(f"Status: SUCCESS")
        print(f"Ticker: {data.get('ticker')}")
        print(f"Current Price in main response: {data.get('current_price')}")
        
        formula_data = data.get('formula_data', {})
        dcf = formula_data.get('dcf', {})
        
        if dcf:
            print(f"DCF Found:")
            print(f"  Intrinsic Value: {dcf.get('intrinsic_value')}")
            print(f"  Current Price in DCF: {dcf.get('current_price')}")
            print(f"  Margin of Safety: {dcf.get('margin_of_safety')}%")
            print(f"  Discount Rate (WACC): {dcf.get('discount_rate', 0)*100:.2f}%")
            
            if dcf.get('fcf_years'):
                print(f"  First Year Projected FCF: {dcf.get('fcf_years')[0]}")
        else:
            print("DCF data is None or missing.")
            
    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
