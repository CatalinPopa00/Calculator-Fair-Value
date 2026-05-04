from scraper.yahoo import get_company_data
import json

def debug_tsm():
    print("Testing TSM ADR Data Normalization...")
    # get_company_data returns (data, peers)
    data, peers = get_company_data("TSM")
    
    print(f"Ticker: {data.get('ticker')}")
    print(f"Price: {data.get('current_price')}")
    print(f"Trailing EPS (GAAP): {data.get('trailing_eps')}")
    print(f"Adjusted EPS (Non-GAAP): {data.get('adjusted_eps')}")
    
    if data.get('historical_anchors'):
        print("\nHistorical Anchors (Last 2):")
        for a in data['historical_anchors'][:2]:
            print(f"Year: {a['year']}, EPS: {a['eps']}, Revenue: {a['revenue_b']}B, Margin: {a['net_margin_pct']}")

if __name__ == "__main__":
    debug_tsm()
