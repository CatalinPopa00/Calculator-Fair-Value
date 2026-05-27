import urllib.request, json

# Get the FULL API response (not just company_profile) to see what calculateForwardEvEbitda receives
url = 'https://proiect-calculator-fair-value.vercel.app/api/valuation/NOW?t=99998'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = json.loads(urllib.request.urlopen(req, timeout=30).read())

# These are the top-level fields that calculateForwardEvEbitda needs
# Note: the function reads from `data` dict BEFORE it's packaged into company_profile
# So let's check what's in the top-level response
print("=== TOP-LEVEL RESPONSE FIELDS needed for EV/EBITDA ===")
for k in ['ebitda', 'total_debt', 'total_cash', 'market_cap',
           'forward_eps', 'forward_ebitda', 'net_income', 
           'shares_outstanding', 'current_price', 'revenue',
           'forward_ev_ebitda', 'forward_ev_sales']:
    print(f"  {k}: {resp.get(k)}")

# Also check company_profile
cp = resp.get('company_profile', {})
print()
print("=== COMPANY_PROFILE FIELDS ===")
for k in ['ebitda', 'total_debt', 'total_cash', 'market_cap',
           'forward_eps', 'forward_ebitda', 'net_income',
           'shares_outstanding', 'fwd_pe', 'fwd_ps',
           'forward_ev_ebitda', 'forward_ev_sales']:
    print(f"  {k}: {cp.get(k)}")
