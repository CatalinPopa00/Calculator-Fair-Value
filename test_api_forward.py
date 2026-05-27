"""Test the full API response for competitor_metrics forward fields"""
import json
import urllib.request

url = 'http://localhost:8001/api/valuation/CRM'
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=120) as response:
        data = json.loads(response.read().decode('utf-8'))
        
    profile = data.get('company_profile', {})
    print("=== COMPANY PROFILE (forward fields) ===")
    print(f"  fwd_pe:             {profile.get('fwd_pe')}")
    print(f"  fwd_ps:             {profile.get('fwd_ps')}")
    print(f"  forward_ev_sales:   {profile.get('forward_ev_sales')}")
    print(f"  forward_ev_ebitda:  {profile.get('forward_ev_ebitda')}")
    
    peers = profile.get('competitor_metrics', [])
    print(f"\n=== COMPETITOR METRICS ({len(peers)} peers) ===")
    for p in peers:
        print(f"\n  --- {p.get('ticker')} ---")
        print(f"    forward_pe:        {p.get('forward_pe')}")
        print(f"    forward_ev_sales:  {p.get('forward_ev_sales')}")
        print(f"    forward_ev_ebitda: {p.get('forward_ev_ebitda')}")
        print(f"    pe_ratio:          {p.get('pe_ratio')}")
        print(f"    ps_ratio:          {p.get('ps_ratio')}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
