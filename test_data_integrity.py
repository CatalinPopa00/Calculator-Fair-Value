import os
import sys

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from api.scraper.yahoo import get_company_data

def verify_ticker(ticker):
    print(f"\n--- Verifying Integrity for {ticker} ---")
    data = get_company_data(ticker)
    if not data:
        print("FAILED to fetch data.")
        return

    print(f"Ticker: {data.get('ticker')}")
    print(f"ROE: {data.get('roe'):.4f}" if data.get('roe') else "ROE: N/A")
    print(f"ROA: {data.get('roa'):.4f}" if data.get('roa') else "ROA: N/A")
    print(f"ROIC: {data.get('roic'):.4f}" if data.get('roic') else "ROIC: N/A")
    print(f"Current Ratio: {data.get('current_ratio'):.2f}" if data.get('current_ratio') else "Current Ratio: N/A")
    print(f"Debt-to-Equity: {data.get('debt_to_equity'):.2f}" if data.get('debt_to_equity') else "Debt-to-Equity: N/A")
    print(f"Net Margin: {data.get('net_margin')*100:.2f}%" if data.get('net_margin') else "Net Margin: N/A")
    print(f"Market Cap (Calculated): {data.get('market_cap'):,.0f}")
    
    anchors = data.get('historical_anchors', [])
    if anchors:
        latest = anchors[0]
        print(f"Latest Fiscal Year: {latest['year']}")
        print(f"Anchor ROIC: {latest['roic_pct']}")

# Test with SMCI and NVDA
verify_ticker("SMCI")
verify_ticker("NVDA")
