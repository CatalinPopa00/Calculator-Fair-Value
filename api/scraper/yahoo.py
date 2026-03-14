import yfinance as yf
import urllib.request
import urllib.parse
import json
import concurrent.futures
import time
import random
import requests

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

def get_random_agent():
    return random.choice(USER_AGENTS)

# Global cache for market averages (SPY) with 1-hour TTL
_market_cache = {"data": None, "timestamp": 0}
_risk_free_cache = {"rate": None, "timestamp": 0}

def get_risk_free_rate() -> float:
    """
    Fetches the 10-year Treasury yield (^TNX) as the risk-free rate.
    Uses a 4.2% fallback and 1-hour cache.
    """
    global _risk_free_cache
    now = time.time()
    if _risk_free_cache["rate"] and (now - _risk_free_cache["timestamp"] < 3600):
        return _risk_free_cache["rate"]
        
    try:
        tnx = yf.Ticker("^TNX")
        # currentPrice is usually the yield in percent for ^TNX on yfinance
        rate = tnx.info.get('regularMarketPrice') or tnx.info.get('currentPrice')
        if rate:
            # yfinance returns 4.25 for 4.25%, we need 0.0425
            val = float(rate) / 100.0
            _risk_free_cache = {"rate": val, "timestamp": now}
            return val
    except Exception as e:
        print(f"Error fetching ^TNX: {e}")
        
    return 0.042 # Fallback 4.2%

def get_nasdaq_earnings_growth(ticker: str, trailing_eps: float) -> float:
    """Fetches the 1-year forward earnings growth estimate from Nasdaq."""
    if not trailing_eps or trailing_eps <= 0:
        return None
    try:
        url = f'https://api.nasdaq.com/api/analyst/{ticker.upper()}/earnings-forecast'
        req = urllib.request.Request(url, headers={'User-Agent': get_random_agent()})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            
        rows = data.get('data', {}).get('yearlyForecast', {}).get('rows', [])
        if rows:
            # First row is usually the next fiscal year
            fwd_eps_nasdaq = float(rows[0].get('consensusEPSForecast', 0))
            if fwd_eps_nasdaq > 0:
                return (fwd_eps_nasdaq - trailing_eps) / trailing_eps
    except Exception as e:
        print(f"Error fetching Nasdaq growth for {ticker}: {e}")
    return None

def get_period_labels(ticker_info: dict) -> dict:
    """
    Returns a mapping from '0q', '+1q', '0y', '+1y' to human-readable 
    labels like 'Q1 2026', 'FY 2026' based on fiscal year end.
    """
    from datetime import datetime
    now = datetime.now()
    curr_year = now.year
    curr_month = now.month
    
    # fiscalYearEnd is usually the timestamp of the last month/day
    fye_timestamp = ticker_info.get('fiscalYearEnd')
    # mostRecentQuarter is timestamp of the last reported quarter
    mrq_timestamp = ticker_info.get('mostRecentQuarter')
    
    mapping = {
        "0q": "Current Quarter",
        "+1q": "Next Quarter",
        "0y": f"FY {curr_year}",
        "+1y": f"FY {curr_year + 1}"
    }
    
    try:
        if mrq_timestamp:
            mrq_dt = datetime.fromtimestamp(mrq_timestamp)
            # If MRQ is very recent (within 4 months), we assume it's the latest finished.
            # Otherwise, 0y is likely the current year we are in.
            
            # For Adobe (ADBE): MRQ might be Feb 2026. Fiscal year ends Nov.
            # So FY 2026 started Dec 2025.
            # In March 2026, 0y is FY 2026.
            pass
            
        # Simplified but effective mapping for now:
        # Detect if we are already 'deep' into the year
        # most companies 0y = current year.
        # However, some companies are advanced.
        
        # Let's use a more robust logic if possible or stick to simple Next/Current 
        # but with years attached.
        mapping["0y"] = f"FY {curr_year}"
        mapping["+1y"] = f"FY {curr_year + 1}"
        
        # If we have MRQ, we can try to guess quarter.
        # But for now, let's at least prepend years to 0y/+1y.
    except:
        pass
        
    return mapping

def resolve_company_name(query: str) -> str:
    """Uses Yahoo Finance search to resolve a company name to a ticker symbol."""
    for attempt in range(3):
        try:
            url = f'https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}'
            req = urllib.request.Request(url, headers={'User-Agent': get_random_agent()})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read())
                quotes = data.get('quotes', [])
                for q in quotes:
                    if q.get('quoteType') == 'EQUITY':
                        return q.get('symbol')
                if quotes:
                    return quotes[0].get('symbol')
        except Exception as e:
            if "429" in str(e) or attempt == 2:
                print(f"Error resolving name {query}: {e}")
            time.sleep(1 + attempt)
    return query

def search_companies(query: str) -> list:
    """Uses Yahoo Finance search to get an autocomplete list of companies."""
    for attempt in range(3):
        try:
            url = f'https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}'
            req = urllib.request.Request(url, headers={'User-Agent': get_random_agent()})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read())
                quotes = data.get('quotes', [])
                results = []
                for q in quotes:
                    if q.get('quoteType') in ['EQUITY', 'ETF'] and q.get('symbol'):
                        exch = q.get('exchDisp') or q.get('exchange', '')
                        name = q.get('shortname') or q.get('longname', q.get('symbol'))
                        if exch:
                            name = f"{name} ({exch})"
                        results.append({
                            "ticker": q.get('symbol'),
                            "name": name
                        })
                    if len(results) >= 10:
                        break
                return results
        except Exception as e:
            if "429" in str(e) or attempt == 2:
                print(f"Error fetching search results for {query}: {e}")
            time.sleep(1 + attempt)
    return []

def get_company_data(ticker_symbol: str):
    """
    Fetches comprehensive data from Yahoo Finance as the primary/fallback data source.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # Parallelize data fetching using ThreadPoolExecutor
        # fetching info, cashflow, financials, and balance_sheet simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_info = executor.submit(lambda: stock.info)
            future_cf = executor.submit(lambda: stock.cashflow)
            future_fin = executor.submit(lambda: stock.financials)
            future_bs = executor.submit(lambda: stock.balance_sheet)
            
            # Wait for main info first as it is critical
            try:
                info = future_info.result(timeout=10)
            except Exception:
                info = {}

        # If it's a name instead of a ticker, Yahoo might return empty/basic info. Fallback to search query.
        if not info or ('shortName' not in info and 'currentPrice' not in info and 'regularMarketPrice' not in info):
            resolved = resolve_company_name(ticker_symbol)
            if resolved and resolved != ticker_symbol:
                ticker_symbol = resolved
                stock = yf.Ticker(ticker_symbol)
                # Re-run parallel fetch for the resolved ticker
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    future_info = executor.submit(lambda: stock.info)
                    future_cf = executor.submit(lambda: stock.cashflow)
                    future_fin = executor.submit(lambda: stock.financials)
                    future_bs = executor.submit(lambda: stock.balance_sheet)
                    try:
                        info = future_info.result(timeout=10)
                    except Exception:
                        info = {}

        # Basic Price and Identifying Info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        name = info.get('shortName', ticker_symbol)
        sector = info.get('sector')
        industry = info.get('industry')
        
        # Start background fetches while processing info
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as nasdaq_executor:
            future_growth = nasdaq_executor.submit(get_nasdaq_earnings_growth, ticker_symbol, info.get('trailingEps'))
            future_est = nasdaq_executor.submit(lambda: stock.earnings_estimate)

            # Valuation Multiples & EPS
            trailing_eps = info.get('trailingEps') or info.get('epsTrailingTwelveMonths')
            forward_eps = info.get('forwardEps')
            pe_ratio = info.get('trailingPE')
            forward_pe = info.get('forwardPE')
            ps_ratio = info.get('priceToSalesTrailing12Months')
            
            # 1. Try YF earnings_estimate - HIGHEST PRIORITY for consensus-based valuation
            try:
                ef = future_est.result(timeout=2)
                if ef is not None and not ef.empty:
                    # Smart selection: pick healthiest forward year (0y vs +1y)
                    g_0y = ef.loc['0y'].get('growth') if '0y' in ef.index else None
                    g_1y = ef.loc['+1y'].get('growth') if '+1y' in ef.index else None
                    
                    labels = get_period_labels(info)
                    
                    if g_0y is not None and g_0y > 0.02:
                        eps_growth = float(g_0y)
                        eps_growth_period = labels.get('0y', 'Current Year')
                    elif g_1y is not None:
                        eps_growth = float(g_1y)
                        eps_growth_period = labels.get('+1y', 'Next Year')
                    elif g_0y is not None:
                        eps_growth = float(g_0y)
                        eps_growth_period = labels.get('0y', 'Current Year')
            except Exception:
                pass
            
            # 2. Try Nasdaq growth (fallback)
            if eps_growth is None:
                eps_growth = future_growth.result(timeout=5)
                if eps_growth: eps_growth_period = "Nasdaq Forecast"

            # 3. Fallback to info.get('earningsGrowth')
            if eps_growth is None:
                eps_growth = info.get('earningsGrowth')
                eps_growth_period = "Trailing Growth"
                if not eps_growth and forward_eps and trailing_eps and trailing_eps > 0:
                    eps_growth = (forward_eps - trailing_eps) / trailing_eps
                elif not eps_growth:
                    eps_growth = info.get('revenueGrowth', 0.05)
            
        # Continue with other info data
        peg_ratio = None
        if pe_ratio and eps_growth and eps_growth > 0:
            peg_ratio = pe_ratio / (eps_growth * 100)
        
        if not peg_ratio:
            peg_ratio = info.get('pegRatio') or info.get('trailingPegRatio')
            
        # Financials for DCF & Margins
        fcf = info.get('freeCashflow')
        if fcf is None:
            fcf = info.get('operatingCashflow')
        shares_outstanding = info.get('sharesOutstanding')
        total_cash = info.get('totalCash')
        total_debt = info.get('totalDebt')
        gross_margins = info.get('grossMargins')
        profit_margins = info.get('profitMargins')
        revenue = info.get('totalRevenue')
        market_cap = info.get('marketCap')

        # Scoring Metrics
        debt_to_equity = info.get('debtToEquity')
        
        # Fallback for Financials/Banks
        if debt_to_equity is None and info.get('totalDebt') and info.get('bookValue') and shares_outstanding:
            equity = info.get('bookValue') * shares_outstanding
            if equity > 0:
                debt_to_equity = (info.get('totalDebt') / equity) * 100.0

        if debt_to_equity is not None:
            try:
                debt_to_equity = float(debt_to_equity) / 100.0
            except (ValueError, TypeError):
                debt_to_equity = None

        current_ratio = info.get('currentRatio')
        if current_ratio is None and info.get('sector') == 'Financial Services':
            current_ratio = 1.0

        roic = info.get('returnOnCapitalEmployed') or info.get('returnOnAssets') or info.get('returnOnEquity')

        # Dividends
        dividend_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate')
        dividend_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield')
        payout_ratio = info.get('payoutRatio')

        # FCF Trend - using already fetched future_cf
        fcf_history = []
        historic_fcf_growth = None
        cf = None  # Store for reuse in historical trends
        try:
            cf = future_cf.result(timeout=10)
            if cf is not None and not cf.empty:
                fcf_y = []
                if 'Free Cash Flow' in cf.index:
                    fcf_y = cf.loc['Free Cash Flow'].dropna().head(5).tolist()
                elif 'Operating Cash Flow' in cf.index:
                    fcf_y = cf.loc['Operating Cash Flow'].dropna().head(5).tolist()
                
                if fcf_y:
                    fcf_history = fcf_y[:3]
                    if len(fcf_y) >= 2:
                        yoy_rates = []
                        for i in range(len(fcf_y)-1):
                            new_val, old_val = fcf_y[i], fcf_y[i+1]
                            if old_val != 0:
                                yoy_rates.append((new_val - old_val) / abs(old_val))
                        if yoy_rates:
                            historic_fcf_growth = sum(yoy_rates) / len(yoy_rates)
        except Exception:
            pass
            
        # Historic EPS growth - using already fetched future_fin
        historic_eps_growth = None
        financials = None  # Store for reuse in interest coverage and historical trends
        try:
            financials = future_fin.result(timeout=10)
            if financials is not None and not financials.empty:
                indices = financials.index
                eps_row = None
                if 'Diluted EPS' in indices: eps_row = financials.loc['Diluted EPS']
                elif 'Basic EPS' in indices: eps_row = financials.loc['Basic EPS']
                
                if eps_row is not None:
                    eps_vals = eps_row.dropna().head(5).tolist()
                    if len(eps_vals) >= 2:
                        yoy_rates = []
                        for i in range(len(eps_vals)-1):
                            new_val, old_val = eps_vals[i], eps_vals[i+1]
                            if old_val != 0:
                                yoy_rates.append((new_val - old_val) / abs(old_val))
                        if yoy_rates:
                            historic_eps_growth = sum(yoy_rates) / len(yoy_rates)
        except Exception:
            pass
            
        # Interest coverage & EBIT Margin — reuse already-fetched financials
        interest_coverage = None
        ebit_margin = None
        try:
            if financials is not None and not financials.empty:
                ebit = financials.loc['EBIT'].dropna() if 'EBIT' in financials.index else None
                if ebit is None and 'Net Income' in financials.index:
                    ebit = financials.loc['Net Income'].dropna()
                    
                if ebit is not None:
                    # Interest Coverage
                    if 'Interest Expense' in financials.index:
                        interest = financials.loc['Interest Expense'].dropna()
                        if not ebit.empty and not interest.empty:
                            ebit_val = ebit.iloc[0]
                            int_val = abs(interest.iloc[0])
                            if int_val > 0:
                                interest_coverage = ebit_val / int_val
                    
                    # EBIT Margin
                    if 'Total Revenue' in financials.index:
                        rev = financials.loc['Total Revenue'].dropna()
                        if not ebit.empty and not rev.empty:
                            e_val = ebit.iloc[0]
                            r_val = rev.iloc[0]
                            if r_val > 0:
                                ebit_margin = e_val / r_val
        except Exception:
            pass
            
        # FWD P/S Estimate
        fwd_ps = info.get('priceToSalesTrailing12Months') # fallback
        try:
            # Approximate forward P/S using current market cap and estimated forward revenue
            # Or use trailing P/S if forward isn't directly available
            fwd_ps = info.get('forwardPE') * (info.get('forwardEps') / (info.get('totalRevenue')/info.get('sharesOutstanding'))) if info.get('forwardPE') and info.get('forwardEps') and info.get('totalRevenue') and info.get('sharesOutstanding') else info.get('priceToSalesTrailing12Months')
        except:
            pass
            
        # Next 3Y Rev Est (Approximated if not directly available via yfinance info)
        # Using revenueGrowth as a proxy for the next 3 years if specific analyst estimates aren't pulled
        next_3y_rev_est = info.get('revenueGrowth')

        # Historic Buyback Rate — reuse already-fetched balance_sheet
        historic_buyback_rate = None
        try:
            bs = future_bs.result(timeout=10)
            if bs is not None and not bs.empty:
                if 'Ordinary Shares Number' in bs.index:
                    shares_row = bs.loc['Ordinary Shares Number'].dropna()
                elif 'Share Issued' in bs.index:
                    shares_row = bs.loc['Share Issued'].dropna()
                elif 'Common Stock' in bs.index:
                    shares_row = bs.loc['Common Stock'].dropna()
                else:
                    shares_row = None

                if shares_row is not None and len(shares_row) >= 2:
                    vals = shares_row.head(3).tolist()  # newest first
                    yoy_rates = []
                    for i in range(len(vals) - 1):
                        s_new = vals[i]
                        s_old = vals[i + 1]
                        if s_old > 0:
                            change = (s_old - s_new) / s_old  # positive means reduction (buyback)
                            yoy_rates.append(change)
                    if yoy_rates:
                        historic_buyback_rate = sum(yoy_rates) / len(yoy_rates)
                        historic_buyback_rate = max(0.0, historic_buyback_rate)  # clamp: ignore share issuance
        except Exception:
            pass

        # Historical Trends — reuse already-fetched financials and cashflow
        historical_trends = []
        try:
            cashflow = cf  # Already fetched above
            if financials is not None and not financials.empty and cashflow is not None and not cashflow.empty:
                import pandas as pd
                # Find common columns, sort by date descending
                cols = list(set(financials.columns).intersection(cashflow.columns))
                cols.sort(reverse=True)
                years = cols[:10]  # Try to grab up to 10 years, though yfinance usually limits to 4 free
                
                for year in years:
                    rev = None
                    if 'Total Revenue' in financials.index:
                        rev_val = financials.loc['Total Revenue', year]
                        rev = float(rev_val) if not pd.isna(rev_val) else None
                        
                    ni = None
                    if 'Net Income' in financials.index:
                        ni_val = financials.loc['Net Income', year]
                        ni = float(ni_val) if not pd.isna(ni_val) else None
                        
                    fcf_val = None
                    if 'Free Cash Flow' in cashflow.index:
                        fcf_tmp = cashflow.loc['Free Cash Flow', year]
                        fcf_val = float(fcf_tmp) if not pd.isna(fcf_tmp) else None
                    
                    margin = (ni / rev) if (ni and rev and rev > 0) else None
                    
                    year_str = year.year if hasattr(year, 'year') else str(year)[:4]
                    
                    historical_trends.append({
                        "year": year_str,
                        "revenue": rev,
                        "net_margin": margin,
                        "fcf": fcf_val
                    })
        except Exception as e:
            print(f"Historical trends format issue: {e}")

        return {
            "ticker": ticker_symbol.upper(),
            "name": name,
            "current_price": current_price,
            "sector": sector,
            "industry": industry,
            "trailing_eps": trailing_eps,
            "peg_ratio": peg_ratio,
            "pe_ratio": pe_ratio,
            "forward_pe": forward_pe,
            "ps_ratio": ps_ratio,
            "eps_growth": eps_growth,
            "fcf": fcf,
            "historic_fcf_growth": historic_fcf_growth,
            "historic_buyback_rate": historic_buyback_rate,
            "shares_outstanding": shares_outstanding,
            "total_cash": total_cash,
            "total_debt": total_debt,
            "gross_margins": gross_margins,
            "profit_margins": profit_margins,
            "revenue": revenue,
            "market_cap": market_cap,
            "current_ratio": current_ratio,
            "roic": roic,
            "interest_coverage": interest_coverage,
            "debt_to_equity": debt_to_equity,
            "fcf_history": fcf_history,
            "dividend_rate": dividend_rate,
            "dividend_yield": dividend_yield,
            "payout_ratio": payout_ratio,
            "historic_eps_growth": historic_eps_growth,
            "historical_trends": historical_trends,
            "forward_eps": forward_eps,
            "ebit_margin": ebit_margin,
            "fwd_ps": fwd_ps,
            "next_3y_rev_est": next_3y_rev_est,
            "beta": info.get('beta')
        }
    except Exception as e:
        print(f"Error fetching Yahoo Data for {ticker_symbol}: {e}")
        return None

def get_competitors_data(target_ticker: str, sector: str, industry: str, market_cap: float = 0, limit: int = 4) -> list:
    """
    Find relevant industry peers using multiple search strategies:
      1. Yahoo screener (sector + region + market cap) with industry post-filter
      2. recommendationsbysymbol with industry validation
      3. Yahoo search fallback (industry keyword search)
    Returns a list of dictionaries (from get_lightweight_company_data).
    """
    target_ticker = target_ticker.upper()
    peer_data = []

    # Strategy 1: Authenticated screener → get same-sector US stocks → filter by industry
    if sector and industry:
        try:
            # Use yfinance's authenticated session for the screener
            stock = yf.Ticker(target_ticker)
            
            payload = {
                "offset": 0, "size": 50, "sortField": "intradaymarketcap", "sortType": "DESC",
                "quoteType": "EQUITY",
                "query": {"operator": "AND", "operands": [
                    {"operator": "eq", "operands": ["sector", sector]},
                    {"operator": "eq", "operands": ["region", "us"]},
                ]},
                "userId": "", "userIdType": "guid"
            }
            resp = stock._data.post(
                'https://query2.finance.yahoo.com/v1/finance/screener',
                body=payload, timeout=10
            )
            if resp.status_code == 200:
                sdata = resp.json()
                candidates = []
                for q in sdata.get('finance', {}).get('result', [{}])[0].get('quotes', []):
                    sym = (q.get('symbol') or '').upper()
                    if sym and sym != target_ticker:
                        candidates.append(sym)

                # Fetch lightweight data in parallel and filter by industry
                if candidates:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(candidates), 10)) as exc:
                        futures = {exc.submit(get_lightweight_company_data, t): t for t in candidates}
                        for future in concurrent.futures.as_completed(futures, timeout=25):
                            try:
                                data = future.result(timeout=10)
                                if data and data.get('industry') == industry:
                                    peer_data.append(data)
                                if len(peer_data) >= limit:
                                    break
                            except Exception:
                                pass
        except Exception as e:
            print(f"Screener strategy failed: {e}")

    # Strategy 2: recommendationsbysymbol + industry validation
    if len(peer_data) < limit:
        existing_tickers = {p['ticker'] for p in peer_data}
        try:
            url = f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/{target_ticker}"
            headers = {'User-Agent': get_random_agent()}
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                rdata = r.json()
                recs = rdata.get('finance', {}).get('result', [{}])[0].get('recommendedSymbols', [])
                rec_syms = [rec['symbol'].upper() for rec in recs
                           if rec.get('symbol') and rec['symbol'].upper() != target_ticker
                           and rec['symbol'].upper() not in existing_tickers]
                
                if rec_syms:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(rec_syms), 5)) as exc:
                        futures = {exc.submit(get_lightweight_company_data, t): t for t in rec_syms}
                        for future in concurrent.futures.as_completed(futures, timeout=15):
                            try:
                                data = future.result(timeout=10)
                                if data:
                                    # Prefer same-industry, but accept same-sector as last resort
                                    if data.get('industry') == industry:
                                        peer_data.insert(0, data)  # prioritize same-industry
                                    elif not industry or len(peer_data) < limit:
                                        peer_data.append(data)
                                if len(peer_data) >= limit:
                                    break
                            except Exception:
                                pass
        except Exception as e:
            print(f"Recommendations strategy failed: {e}")

    # Strategy 3: Search Fallback (Industry keyword search)
    if len(peer_data) < limit:
        existing_tickers = {p['ticker'] for p in peer_data}
        try:
            query = industry or sector or target_ticker
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}"
            headers = {'User-Agent': get_random_agent()}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                search_syms = []
                for q in r.json().get('quotes', []):
                    sym = (q.get('symbol') or '').upper()
                    if (sym and sym != target_ticker and q.get('quoteType') == 'EQUITY'
                            and sym not in existing_tickers and '.' not in sym):
                        search_syms.append(sym)
                    if len(search_syms) >= limit * 2:
                        break
                
                if search_syms:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(search_syms), 5)) as exc:
                        futures = {exc.submit(get_lightweight_company_data, t): t for t in search_syms}
                        for future in concurrent.futures.as_completed(futures, timeout=15):
                            try:
                                data = future.result(timeout=10)
                                if data and data['ticker'] not in existing_tickers:
                                    peer_data.append(data)
                                    existing_tickers.add(data['ticker'])
                                if len(peer_data) >= limit:
                                    break
                            except Exception:
                                pass
        except Exception as e:
            print(f"Search fallback failed: {e}")

    return peer_data[:limit]

def get_lightweight_company_data(ticker_symbol: str):
    """Fetches a minimal set of data for competitor comparison."""
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        pe = info.get('trailingPE') or info.get('forwardPE')
        peg = info.get('pegRatio') or info.get('trailingPegRatio')
        if not peg and pe and info.get('earningsGrowth'):
            peg = pe / (info.get('earningsGrowth') * 100)
            
        return {
            "ticker": ticker_symbol.upper(),
            "name": info.get('shortName') or info.get('longName') or ticker_symbol,
            "price": info.get('currentPrice') or info.get('regularMarketPrice'),
            "pe_ratio": pe,
            "peg_ratio": peg,
            "industry": info.get('industry')
        }
    except Exception:
        return None


def get_market_averages():
    """
    Returns S&P 500 P/E metrics using SPY as a proxy.
    Includes a 1-hour in-memory cache to reduce network calls.
    """
    global _market_cache
    now = time.time()
    
    # Return cached data if valid (1 hour = 3600 seconds)
    if _market_cache["data"] and (now - _market_cache["timestamp"] < 3600):
        return _market_cache["data"]

    try:
        spy = yf.Ticker("SPY")
        info = spy.info
        data = {
            "trailing_pe": info.get('trailingPE'),
            "forward_pe": info.get('forwardPE') or info.get('trailingPE')
        }
        _market_cache = {"data": data, "timestamp": now}
        return data
    except Exception as e:
        print(f"Error fetching SPY market average: {e}")
        return {
            "trailing_pe": 25.0, # Fallback S&P avg
            "forward_pe": 21.0
        }


def get_period_labels(ticker_info: dict) -> dict:
    """
    Returns a mapping from '0q', '+1q', '+2q', '+3q', '0y', '+1y' to human-readable 
    labels like 'Q1 2026', 'FY 2026' based on fiscal year end.
    """
    from datetime import datetime
    now = datetime.now()
    curr_year = now.year
    curr_q = (now.month - 1) // 3 + 1
    
    mapping = {
        "0q": f"Q{curr_q} {curr_year}",
        "0y": f"FY {curr_year}",
        "+1y": f"FY {curr_year + 1}"
    }
    
    # Calculate next quarters based on current
    q_num = curr_q
    q_year = curr_year
    for i in range(1, 5):
        q_num += 1
        if q_num > 4:
            q_num = 1
            q_year += 1
        
        mapping[f"+{i}q"] = f"Q{q_num} {q_year}"
        
    return mapping

def get_analyst_data(ticker_symbol: str) -> dict:
    """
    Fetches analyst estimates data:
    - Price targets (low / average / high / current)
    - Recommendation (Strong Buy / Buy / Hold / Sell / Strong Sell + counts)
    - EPS estimates (current year, next year, next 5yr CAGR)
    - Revenue estimates (current year, next year)
    - EPS history (actual vs estimate, last 4 quarters)
    """
    try:
        from datetime import datetime
        stock = yf.Ticker(ticker_symbol)
        info  = stock.info
        labels = get_period_labels(info)

        # ── Price Target ─────────────────────────────────────────────────────────
        target_mean  = info.get('targetMeanPrice')
        target_low   = info.get('targetLowPrice')
        target_high  = info.get('targetHighPrice')
        target_median = info.get('targetMedianPrice')
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        upside = ((target_mean - current_price) / current_price * 100) if (target_mean and current_price) else None
        num_analysts = info.get('numberOfAnalystOpinions')

        # ── Analyst Recommendation ───────────────────────────────────────────────
        rec_key = info.get('recommendationKey', '')       # e.g. "buy", "strong_buy"
        rec_mean = info.get('recommendationMean')          # 1=Strong Buy … 5=Strong Sell

        # ── INITIALIZE LISTS ──────────────────────────────────────────────────
        eps_estimates = []
        rev_estimates = []

        # ── Recommendation Counts Fix ──────────────────────────────────────────
        rec_counts = {"strongBuy": 0, "buy": 0, "hold": 0, "sell": 0, "strongSell": 0}
        try:
            rec_df = stock.recommendations_summary
            if rec_df is not None and not rec_df.empty:
                latest = rec_df.iloc[0]
                rec_counts["strongBuy"] = int(latest.get('strongBuy', 0))
                rec_counts["buy"] = int(latest.get('buy', 0))
                rec_counts["hold"] = int(latest.get('hold', 0))
                rec_counts["sell"] = int(latest.get('sell', 0))
                rec_counts["strongSell"] = int(latest.get('strongSell', 0))
        except Exception:
            pass

        # ── Historical Reported Data (EPS and Revenue) ───────────────────────────
        reported_eps = []
        reported_rev = []
        try:
            import pandas as pd
            # EPS History
            eh = stock.earnings_history
            if eh is not None and not eh.empty:
                for idx, row in eh.tail(4).iterrows(): # take up to last 4 reported
                    eps_act = row.get('epsActual') if hasattr(row, 'get') else None
                    eps_est = row.get('epsEstimate') if hasattr(row, 'get') else None
                    surprise_pct = row.get('surprisePercent') if hasattr(row, 'get') else None
                    
                    date_str = "--"
                    if isinstance(idx, (pd.Timestamp, datetime)):
                        q_num = (idx.month - 1) // 3 + 1
                        date_str = f"Q{q_num} {idx.year}"
                    elif idx:
                        date_str = str(idx)

                    val = float(eps_act) if eps_act is not None and not (isinstance(eps_act, float) and pd.isna(eps_act)) else None
                    if val is not None:
                        reported_eps.append({
                            "period": date_str, "avg": val, "status": "reported",
                            "surprise_pct": float(surprise_pct) if surprise_pct is not None and not pd.isna(surprise_pct) else None
                        })
            
            # Revenue History
            istmt = stock.quarterly_income_stmt
            if istmt is not None and not istmt.empty and 'Total Revenue' in istmt.index:
                rev_row = istmt.loc['Total Revenue']
                # rev_row index is dates (descending usually). Take latest 4.
                for col_date in list(rev_row.index)[:4][::-1]: 
                    rev_act = rev_row[col_date]
                    if pd.isna(rev_act): continue
                    
                    date_str = "--"
                    if isinstance(col_date, (pd.Timestamp, datetime)):
                        q_num = (col_date.month - 1) // 3 + 1
                        date_str = f"Q{q_num} {col_date.year}"
                    
                    reported_rev.append({
                        "period": date_str, "avg": float(rev_act), "status": "reported", "surprise_pct": None
                    })
        except Exception as e:
            print(f"[Analyst] Reported history error: {e}")

        # ── Yahoo EPS Estimates ──────────────────────────────────────────────────
        try:
            import pandas as pd
            ef = stock.earnings_estimate
            if ef is not None and not ef.empty:
                for period_idx, row in ef.iterrows():
                    p_key = str(period_idx)
                    avg = row.get('avg') if hasattr(row, 'get') else row.get('Avg')
                    growth = row.get('growth') if hasattr(row, 'get') else row.get('Growth')
                    eps_estimates.append({
                        "period": labels.get(p_key, p_key), "period_code": p_key,
                        "avg": float(avg) if avg is not None and not (isinstance(avg, float) and pd.isna(avg)) else None,
                        "growth": float(growth) if growth is not None and not (isinstance(growth, float) and pd.isna(growth)) else None,
                        "status": "estimate"
                    })
        except Exception as e:
            print(f"[Analyst] Yahoo EPS error: {e}")

        # ── Yahoo Revenue Estimates ─────────────────────────────────────────────
        try:
            import pandas as pd
            rf = stock.revenue_estimate
            if rf is not None and not rf.empty:
                for period_idx, row in rf.iterrows():
                    p_key = str(period_idx)
                    avg = row.get('avg') if hasattr(row, 'get') else None
                    growth = row.get('growth') if hasattr(row, 'get') else None
                    rev_estimates.append({
                        "period": labels.get(p_key, p_key), "period_code": p_key,
                        "avg": float(avg) if avg is not None and not (isinstance(avg, float) and pd.isna(avg)) else None,
                        "growth": float(growth) if growth is not None and not (isinstance(growth, float) and pd.isna(growth)) else None,
                        "status": "estimate"
                    })
        except Exception as e:
            print(f"[Analyst] Yahoo Revenue error: {e}")

        # ── FALLBACK: Nasdaq (fetch missing quarters) ──────────────────────────
        n_data = None
        def fetch_nasdaq():
            try:
                nasdaq_url = f"https://api.nasdaq.com/api/analyst/{ticker_symbol}/earnings-forecast"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
                req = urllib.request.Request(nasdaq_url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return json.loads(resp.read())
            except Exception as ne:
                print(f"Nasdaq fallback fetch failed: {ne}")
                return None

        # Determine if we even need the fallback. Start fetch in background just in case.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_nasdaq = executor.submit(fetch_nasdaq)

            # Wait to see if we actually need it based on yahoo estimates length
            if len([e for e in eps_estimates if 'q' in e['period_code']]) < 4 or len([e for e in rev_estimates if 'q' in e['period_code']]) < 4:
                n_data = future_nasdaq.result()
        

        if n_data:
            # Nasdaq EPS Quarters
            q_forecasts = n_data.get('data', {}).get('quarterlyForecast', {}).get('rows', [])
            for i, qf in enumerate(q_forecasts[:4]):
                p_code = "0q" if i == 0 else f"+{i}q"
                existing = next((e for e in eps_estimates if e['period_code'] == p_code), None)
                avg = qf.get('consensusEPSForecast')
                if avg and avg != "N/A":
                    avg_val = float(str(avg).replace('$', '').replace(',', ''))
                    period_lbl = labels.get(p_code, p_code)
                    if existing:
                        if not existing['avg']: existing['avg'] = avg_val
                        if existing['period'] in ['Current Qtr', 'Next Qtr']: existing['period'] = period_lbl
                    else:
                        eps_estimates.append({"period": period_lbl, "period_code": p_code, "avg": avg_val, "growth": None, "status": "estimate"})
            
            # Nasdaq Revenue Quarters
            r_forecasts = n_data.get('data', {}).get('revenueForecast', {}).get('rows', [])
            for i, rf in enumerate(r_forecasts[:4]):
                p_code = "0q" if i == 0 else f"+{i}q"
                existing = next((e for e in rev_estimates if e['period_code'] == p_code), None)
                avg = rf.get('consensusRevenueForecast')
                if avg and avg != "N/A":
                    avg_str = str(avg).replace('$', '').replace(',', '').replace('B', '').replace('M', '').strip()
                    try:
                        avg_val = float(avg_str)
                        if 'M' in str(avg): avg_val /= 1000.0
                        period_lbl = labels.get(p_code, p_code)
                        if existing:
                            if not existing['avg']: existing['avg'] = avg_val
                            if existing['period'] in ['Current Qtr', 'Next Qtr']: existing['period'] = period_lbl
                        else:
                            rev_estimates.append({"period": period_lbl, "period_code": p_code, "avg": avg_val, "growth": None, "status": "estimate"})
                    except: pass

        # ── PADDING QUARTERS ───────────────────────────────────────────
        # Ensure that +2q and +3q exist even if empty, so the UI aligns
        for prefix in ['0q', '+1q', '+2q', '+3q']:
            if not any(e['period_code'] == prefix for e in eps_estimates):
                eps_estimates.append({"period": labels.get(prefix, prefix), "period_code": prefix, "avg": None, "growth": None, "status": "estimate"})
            if not any(r['period_code'] == prefix for r in rev_estimates):
                rev_estimates.append({"period": labels.get(prefix, prefix), "period_code": prefix, "avg": None, "growth": None, "status": "estimate"})

        # ── POST-PROCESSING: Combine and Sort ───────────────────────────────────
        def sort_key(e):
            code = e.get('period_code', '')
            order = {"0q": 1, "+1q": 2, "+2q": 3, "+3q": 4, "0y": 5, "+1y": 6}
            return order.get(code, 99)

        eps_estimates.sort(key=sort_key)
        rev_estimates.sort(key=sort_key)

        # Extract the current fiscal year from the '0y' (current year) estimate
        current_year_str = str(datetime.now().year)
        for e in eps_estimates:
            if e.get('period_code') == '0y' and e.get('period'):
                # Extract the 4 digit year from the string 'FY 2026' or '2026'
                import re
                match = re.search(r'\d{4}', str(e.get('period')))
                if match:
                    current_year_str = match.group(0)
                break
        
        # Only include reported quarters from the current year
        curr_yr_reported_eps = [e for e in reported_eps if current_year_str in str(e.get('period', ''))]
        reported_eps_periods = {e.get('period') for e in curr_yr_reported_eps if e.get('period')}
        
        # Pull estimates, but exclude any that match a period we already have reported data for
        eps_qtrs = [e for e in eps_estimates if 'q' in e.get('period_code', '') and current_year_str in str(e.get('period', '')) and e.get('period') not in reported_eps_periods]
        eps_years = [e for e in eps_estimates if 'y' in e.get('period_code', '')][:2]
        
        unified_eps = curr_yr_reported_eps + eps_qtrs + eps_years

        curr_yr_reported_rev = [e for e in reported_rev if current_year_str in str(e.get('period', ''))]
        reported_rev_periods = {e.get('period') for e in curr_yr_reported_rev if e.get('period')}

        rev_qtrs = [e for e in rev_estimates if 'q' in e.get('period_code', '') and current_year_str in str(e.get('period', '')) and e.get('period') not in reported_rev_periods]
        rev_years = [e for e in rev_estimates if 'y' in e.get('period_code', '')][:2]
        
        unified_rev = curr_yr_reported_rev + rev_qtrs + rev_years

        # ── EPS growth from estimates ─────────────────────────────────────────────
        # Smart selection: pick the healthiest forward year
        eps_forward_growth = info.get('earningsGrowth', 0.10)
        
        g_0y = None
        g_1y = None
        if eps_estimates:
            for est in eps_estimates:
                if est['period_code'] == '0y': g_0y = est['growth']
                if est['period_code'] == '+1y': g_1y = est['growth']
        
        # Logic: If 0y is positive and stable (>2%), prioritize it.
        # Otherwise (if negative like Uber's -28% or very low), use +1y.
        if g_0y is not None and g_0y > 0.02:
            eps_forward_growth = g_0y
        elif g_1y is not None:
            eps_forward_growth = g_1y
        elif g_0y is not None:
            eps_forward_growth = g_0y

        return {
            "ticker": ticker_symbol.upper(),
            "price_target": {
                "current": current_price,
                "low":    target_low,
                "avg":    target_mean,
                "median": target_median,
                "high":   target_high,
                "upside_pct": upside,
                "num_analysts": num_analysts
            },
            "recommendation": {
                "key":  rec_key,
                "mean": rec_mean,
                "counts": rec_counts
            },
            "eps_5yr_growth": eps_forward_growth,
            "eps_estimates":  unified_eps,
            "rev_estimates":  unified_rev
        }

    except Exception as e:
        print(f"[Analyst] Data fetch failed for {ticker_symbol}: {e}")
        return {"ticker": ticker_symbol.upper(), "error": str(e)}
