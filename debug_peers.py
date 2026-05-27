"""
Debug script to check exactly what data peers have 
and what the proxy functions return.
"""
import json
from scraper.yahoo import get_competitors_data

# Get peers for CRM
peers = get_competitors_data('CRM', limit=3)

print("=" * 80)
print(f"Got {len(peers)} peers")
print("=" * 80)

for p in peers:
    ticker = p.get('ticker', '?')
    print(f"\n--- {ticker} ---")
    print(f"  price:            {p.get('price')}")
    print(f"  forward_eps:      {p.get('forward_eps')}")
    print(f"  forward_revenue:  {p.get('forward_revenue')}")
    print(f"  forward_ebitda:   {p.get('forward_ebitda')}")
    print(f"  market_cap:       {p.get('market_cap')}")
    print(f"  total_debt:       {p.get('total_debt')}")
    print(f"  total_cash:       {p.get('total_cash')}")
    print(f"  ebitda:           {p.get('ebitda')}")
    
    # Simulate the proxy functions
    # calculateForwardPE
    fwd_eps = p.get("forward_eps")
    price = p.get("price")
    fwd_pe = None
    if fwd_eps and price and fwd_eps > 0:
        val = price / fwd_eps
        fwd_pe = val if val > 0 else None
    print(f"  -> forward_pe:        {fwd_pe}")
    
    # calculateForwardEvSales
    mcap = p.get("market_cap") or 0
    debt = p.get("total_debt") or 0
    cash = p.get("total_cash") or 0
    curr_ev = mcap + debt - cash
    fwd_rev = p.get("forward_revenue")
    fwd_ev_sales = None
    if fwd_rev is not None and fwd_rev > 0:
        val = curr_ev / fwd_rev
        fwd_ev_sales = val if val > 0 else None
    print(f"  -> forward_ev_sales:  {fwd_ev_sales}")
    
    # calculateForwardEvEbitda
    fwd_ebitda = p.get("forward_ebitda")
    fwd_ev_ebitda = None
    if fwd_ebitda and fwd_ebitda > 0:
        val = curr_ev / fwd_ebitda
        fwd_ev_ebitda = val if val > 0 else None
    print(f"  -> forward_ev_ebitda: {fwd_ev_ebitda}")

print("\n" + "=" * 80)
print("CONCLUSION: If forward_pe and forward_ev_sales show values above,")
print("then the proxy functions work. The issue is in API response construction.")
