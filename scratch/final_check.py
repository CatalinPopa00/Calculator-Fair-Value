
import sys
import os

# Add the directory to sys.path
sys.path.append(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d\Calculator-Fair-Value-f4d1464ea2b03f0531ce89163a3625517662702d')

from scraper.yahoo import get_company_data

if __name__ == "__main__":
    ticker = "ADBE"
    result = get_company_data(ticker)
    anchors = result.get('historical_anchors', [])
    print(f"Anchors Found: {len(anchors)}")
    for a in anchors:
        print(f"  Year: {a['year']}, Revenue: {a['revenue_b']}B, EPS*: {a['eps']}, Margin: {a['net_margin_pct']}")
    
    # Also check historical_data["years"]
    hist = result.get("historical_data", {})
    print(f"Historical Years: {hist.get('years')}")
