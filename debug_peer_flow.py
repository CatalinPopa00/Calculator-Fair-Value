import yfinance as yf
from scraper.yahoo import get_yahoo_analysis_normalized

# Simulate exactly what fetch_peer_info does inside get_competitors_data
# (lines 3200-3322 of yahoo.py)

ticker = 'NOW'
inf = yf.Ticker(ticker).info

# Get analysis data the same way the scraper does
try:
    analysis = get_yahoo_analysis_normalized(ticker)
except:
    analysis = {'eps': {}, 'rev': {}}

p_price = inf.get('regularMarketPrice') or inf.get('currentPrice')
p_shares = inf.get('impliedSharesOutstanding') or inf.get('sharesOutstanding')

# FWD PE calculation (same as scraper)
fwd_pe_explicit = None
fwd_eps_explicit = None
try:
    e1 = analysis['eps'].get('0y', {})
    if e1.get('avg'):
        fwd_eps_explicit = e1['avg']
        fwd_pe_explicit = p_price / fwd_eps_explicit
except:
    pass
fwd_pe = fwd_pe_explicit or inf.get('forwardPE')

# FWD PS calculation
fwd_ps_explicit = None
fwd_rev_explicit = None
try:
    r1 = analysis['rev'].get('0y', {})
    if r1.get('avg'):
        fwd_rev_explicit = r1['avg']
        if p_shares and p_shares > 0:
            fwd_ps_explicit = p_price / (fwd_rev_explicit / p_shares)
except:
    pass
fwd_ps = fwd_ps_explicit or inf.get('priceToSalesTrailing12Months')

# Build peer dict exactly like scraper does (lines 3287-3314)
p_data = {
    "ticker": ticker,
    "price": p_price,
    "pe_ratio": fwd_pe,
    "market_cap": inf.get('marketCap'),
    "ps_ratio": fwd_ps,
    "revenue": inf.get('totalRevenue'),
    "forward_revenue": fwd_rev_explicit,
    "ev_to_ebitda": inf.get('enterpriseToEbitda'),
    "eps": fwd_eps_explicit or inf.get('forwardEps') or inf.get('trailingEps'),
    "forward_eps": fwd_eps_explicit or inf.get('forwardEps'),
    "total_cash": inf.get('totalCash'),
    "total_debt": inf.get('totalDebt'),
    "ebitda": inf.get('ebitda'),
    "forward_ebitda": inf.get('forwardEbitda'),
    "net_income": inf.get('netIncomeToCommon'),
    "shares_outstanding": p_shares,
}

print("=== Peer data dict (as scraper builds it) ===")
for k, v in p_data.items():
    print(f"  {k}: {v}")

print()
print(f"  fwd_pe_explicit: {fwd_pe_explicit}")
print(f"  fwd_ps_explicit: {fwd_ps_explicit}")
print(f"  fwd_rev_explicit: {fwd_rev_explicit}")
print(f"  fwd_eps_explicit: {fwd_eps_explicit}")

# Now check: will the scraper ACTUALLY include ebitda/net_income?
# Look at lines 3300 and 3310
print()
print("=== KEY QUESTION: Does the scraper dict have the fields calculateForwardEvEbitda needs? ===")
print(f"  ebitda present and > 0? {bool(p_data.get('ebitda') and p_data['ebitda'] > 0)}")
print(f"  net_income present? {bool(p_data.get('net_income'))}")
print(f"  forward_eps present? {bool(p_data.get('forward_eps'))}")
print(f"  shares_outstanding present? {bool(p_data.get('shares_outstanding'))}")
print(f"  total_debt present? {bool(p_data.get('total_debt'))}")
print(f"  total_cash present? {bool(p_data.get('total_cash'))}")
