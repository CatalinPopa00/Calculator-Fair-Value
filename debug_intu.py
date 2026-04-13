from api.scraper.yahoo import get_company_data, get_competitors_data, get_market_averages, get_risk_free_rate
from api.models.valuation import (
    calculate_peter_lynch, 
    calculate_peg_fair_value, 
    calculate_dcf, 
    calculate_relative_valuation,
    calculate_dcf_sensitivity,
    calculate_reverse_dcf
)
import json
import math

def test_full_valuation(ticker):
    print(f"Testing {ticker} full valuation...")
    try:
        # 1. Scrape Yahoo Data
        data = get_company_data(ticker)
        if not data:
            print("Failed: get_company_data returned None")
            return
            
        current_price = data["current_price"]
        print(f"Current Price: {current_price}")
    
        # 2. Get Competitors
        sector = data.get("sector")
        industry = data.get("industry")
        target_market_cap = data.get("market_cap") or 0.0
        peers_data = get_competitors_data(ticker, sector, industry, float(target_market_cap))
        print(f"Peers: {[p.get('ticker') if isinstance(p, dict) else p for p in peers_data]}")
        
        market_data = get_market_averages()
        
        # 3. Compute Valuations
        print("Computing Peter Lynch...")
        lynch_result = calculate_peter_lynch(current_price, data.get("trailing_eps"), data.get("eps_growth"), data.get("pe_ratio"))
        
        print("Computing PEG...")
        peg_value = calculate_peg_fair_value(data.get("trailing_eps"), data.get("eps_growth"))
        
        print("Computing Relative...")
        relative_value = calculate_relative_valuation(ticker, data, peers_data)
        
        print("Computing DCF...")
        fcf = data.get("fcf")
        shares = data.get("shares_outstanding")
        eps_growth = data.get("eps_growth", 0.05) if data.get("eps_growth") is not None else 0.05
        
        risk_free_rate = get_risk_free_rate()
        beta = data.get("beta") or 1.0
        dynamic_wacc = risk_free_rate + (beta * 0.055)
        
        if fcf and shares and fcf > 0:
            dcf_result = calculate_dcf(fcf, eps_growth, dynamic_wacc, 0.02, shares, data.get("total_cash"), data.get("total_debt"))
            dcf_sensitivity = calculate_dcf_sensitivity(fcf, eps_growth, shares, data.get("total_cash"), data.get("total_debt"), 5, dynamic_wacc, 0.02)
            reverse_dcf_growth = calculate_reverse_dcf(current_price, fcf, dynamic_wacc, 0.02, shares, data.get("total_cash"), data.get("total_debt"), 5)
            print("DCF Success")
        else:
            print(f"DCF Skipped: fcf={fcf}, shares={shares}")

        print("\nALL CALCULATIONS COMPLETED SUCCESSFULY")

    except Exception as e:
        print(f"\nCRASH DETECTED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_valuation("INTU")
