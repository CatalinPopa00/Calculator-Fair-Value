import urllib.request, json

# Check the LIVE API response to see ALL fields on each peer
url = 'https://proiect-calculator-fair-value.vercel.app/api/valuation/NOW?t=99999'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
data = json.loads(urllib.request.urlopen(req, timeout=30).read())
c = data.get('company_profile', {})

# Target company fields
print("=== TARGET (NOW) ===")
for k in ['ebitda', 'forward_ebitda', 'net_income', 'total_debt', 'total_cash',
           'market_cap', 'shares_outstanding', 'forward_eps', 'forward_ev_ebitda',
           'forward_ev_sales', 'fwd_ps', 'fwd_pe']:
    print(f"  {k}: {c.get(k)}")

print()
# Peer fields
for p in c.get('competitor_metrics', []):
    print(f"=== PEER: {p.get('ticker')} ===")
    for k in sorted(p.keys()):
        print(f"  {k}: {p[k]}")
    print()
