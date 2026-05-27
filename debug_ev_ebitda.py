import yfinance as yf

# Simulate exactly what calculateForwardEvEbitda does for a peer
# using the data that get_competitors_data would provide

ticker = 'NOW'
inf = yf.Ticker(ticker).info

# This is what scraper sends for a peer (lines 3287-3314 of yahoo.py)
p = {
    "ticker": ticker,
    "price": inf.get('regularMarketPrice') or inf.get('currentPrice'),
    "market_cap": inf.get('marketCap'),
    "total_debt": inf.get('totalDebt'),
    "total_cash": inf.get('totalCash'),
    "ebitda": inf.get('ebitda'),
    "forward_ebitda": inf.get('forwardEbitda'),  # This will be None
    "net_income": inf.get('netIncomeToCommon'),
    "shares_outstanding": inf.get('impliedSharesOutstanding') or inf.get('sharesOutstanding'),
    "forward_eps": inf.get('forwardEps'),
}

print("=== Peer data as sent by scraper ===")
for k, v in p.items():
    print(f"  {k}: {v}")

# Now simulate calculateForwardEvEbitda
mcap = p.get("market_cap") or 0
debt = p.get("total_debt") or 0
cash = p.get("total_cash") or 0
curr_ev = mcap + debt - cash
print(f"\n=== EV Calculation ===")
print(f"  mcap={mcap}, debt={debt}, cash={cash}")
print(f"  curr_ev = {curr_ev}")

fwd_ebitda = p.get("forward_ebitda") or p.get("forwardEbitda")
print(f"  fwd_ebitda (raw): {fwd_ebitda}")

if not fwd_ebitda or fwd_ebitda <= 0:
    fwd_eps = p.get("forward_eps") or p.get("fwd_eps")
    shares = p.get("shares_outstanding")
    print(f"  fwd_eps: {fwd_eps}")
    print(f"  shares: {shares}")
    
    if not shares or shares <= 0:
        price = p.get("price") or p.get("current_price")
        if mcap and price and price > 0:
            shares = mcap / price
            print(f"  shares (computed from mcap/price): {shares}")
    
    if fwd_eps and shares and shares > 0:
        fwd_ni = fwd_eps * shares
        ebitda = p.get("ebitda") or 0
        ni = p.get("net_income") or 0
        tax_int_da = ebitda - ni
        fwd_ebitda = fwd_ni + tax_int_da
        print(f"  fwd_ni (eps*shares): {fwd_ni}")
        print(f"  ebitda (TTM): {ebitda}")
        print(f"  ni (TTM): {ni}")
        print(f"  tax_int_da: {tax_int_da}")
        print(f"  fwd_ebitda (computed): {fwd_ebitda}")

if fwd_ebitda and fwd_ebitda > 0:
    val = curr_ev / fwd_ebitda
    print(f"\n  >>> FWD EV/EBITDA = {val:.4f}")
else:
    print(f"\n  >>> FWD EV/EBITDA = None (fwd_ebitda={fwd_ebitda})")

# Compare with Yahoo's TTM
print(f"\n  Yahoo TTM EV/EBITDA: {inf.get('enterpriseToEbitda')}")
