import sys
import os
import json
import asyncio

# Setup path to include the current directory for imports
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d')

from api.scraper.yahoo import get_company_data, get_market_averages
from api.index import deep_clean_data

async def test_fixes():
    ticker = "ADBE"
    print(f"Testing local fixes for {ticker}...")
    
    # 1. Test Market Averages (SPY)
    market = get_market_averages()
    print(f"Market Averages: {market}")
    if market.get('trailing_pe') is None:
        print("FAILED: Market P/E is still None")
    else:
        print("PASSED: Market P/E found")

    # 2. Test Company Data (EPS Growth & FCF Trend)
    data = get_company_data(ticker)
    
    # Check EPS Estimates for growth consistency
    eps_est = data.get("eps_estimates", [])
    fy0 = next((e for e in eps_est if "FY 2026" in e['period']), None)
    
    if fy0:
        print(f"FY 2026 EPS: {fy0.get('avg')}, Growth: {fy0.get('growth'):.2%}")
        if 0.10 < fy0.get('growth') < 0.15:
            print("PASSED: FY 2026 Growth is locally calculated against the correct base (~12%)")
        else:
            print(f"FAILED: FY 2026 Growth is still outlier ({fy0.get('growth'):.2%})")
            
    # Check FCF Trend and Health Score
    anchors = data.get("historical_anchors", [])
    print(f"DEBUG: Historical Anchors (FCF_B): {[ (a.get('year'), a.get('fcf_b')) for a in anchors ]}")
    actual_fcf = [a.get("fcf_b") for a in anchors if a.get("fcf_b") is not None and "(Est)" not in str(a.get("year", ""))]
    
    fcf_trend = "Flat"
    if len(actual_fcf) >= 2:
        actual_fcf_chrono = list(reversed(actual_fcf))
        last_fcf = actual_fcf_chrono[-1]
        prev_avg = sum(actual_fcf_chrono[:-1]) / len(actual_fcf_chrono[:-1]) if len(actual_fcf_chrono) > 1 else actual_fcf_chrono[0]
        print(f"DEBUG: last_fcf (newest)={last_fcf}, prev_avg={prev_avg}")
        if last_fcf > prev_avg * 1.05:
            fcf_trend = "Growing"
        elif last_fcf < prev_avg * 0.95:
            fcf_trend = "Declining"
    
    print(f"Detected FCF Trend: {fcf_trend}")
    if fcf_trend == "Growing":
        print("PASSED: FCF Trend correctly detected as 'Growing'")
    else:
        print("FAILED: FCF Trend still 'Flat' or 'Declining'")

if __name__ == "__main__":
    asyncio.run(test_fixes())
