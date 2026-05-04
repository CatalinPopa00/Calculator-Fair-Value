import yfinance as yf

# Test availability of key multiples across a range of tickers
tickers = ["ADBE", "CRM", "NOW", "INTU", "MSFT", "AAPL", "META", "NVDA", "JPM", "XOM"]

for t in tickers:
    try:
        info = yf.Ticker(t).info
        mcap = info.get('marketCap')
        fcf = info.get('freeCashflow')
        ocf = info.get('operatingCashflow')
        pe = info.get('trailingPE')
        ps = info.get('priceToSalesTrailing12Months')
        pb = info.get('priceToBook')
        ev_ebitda = info.get('enterpriseToEbitda')
        
        pfcf = None
        if fcf and mcap and fcf > 0:
            pfcf = mcap / fcf
        elif ocf and mcap and ocf > 0:
            pfcf = mcap / ocf
        
        print(f"{t:6s} | P/E={str(round(pe,1)) if pe else 'MISS':>8s} | P/S={str(round(ps,1)) if ps else 'MISS':>6s} | P/B={str(round(pb,1)) if pb else 'MISS':>6s} | EV/EBITDA={str(round(ev_ebitda,1)) if ev_ebitda else 'MISS':>6s} | P/FCF={str(round(pfcf,1)) if pfcf else 'MISS':>6s}  (fcf={fcf}, ocf={ocf})")
    except Exception as e:
        print(f"{t}: ERROR - {e}")
