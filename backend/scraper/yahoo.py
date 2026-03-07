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
        # fetching info, cashflow, and financials simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_info = executor.submit(lambda: stock.info)
            future_cf = executor.submit(lambda: stock.cashflow)
            future_fin = executor.submit(lambda: stock.financials)
            
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
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    future_info = executor.submit(lambda: stock.info)
                    future_cf = executor.submit(lambda: stock.cashflow)
                    future_fin = executor.submit(lambda: stock.financials)
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
            
            # 1. Try YF earnings_estimate for +1y (Forward Year) - HIGHEST PRIORITY for consistency
            try:
                ef = future_est.result(timeout=2)
                if ef is not None and not ef.empty and '+1y' in ef.index:
                    growth_val = ef.loc['+1y'].get('growth')
                    if growth_val is not None:
                        eps_growth = float(growth_val)
            except Exception:
                pass
            
            # 2. Try Nasdaq growth
            if eps_growth is None:
                eps_growth = future_growth.result(timeout=5)

            # 3. Fallback to info.get('earningsGrowth') or trailing/forward calc
            if eps_growth is None:
                eps_growth = info.get('earningsGrowth')
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
        shares_outstanding = info.get('sharesOutstanding')
        total_cash = info.get('totalCash')
        total_debt = info.get('totalDebt')
        gross_margins = info.get('grossMargins')
        profit_margins = info.get('profitMargins')
        revenue = info.get('totalRevenue')
        market_cap = info.get('marketCap')

        # Scoring Metrics
        debt_to_equity = info.get('debtToEquity')
        if debt_to_equity is not None:
            try:
                debt_to_equity = float(debt_to_equity) / 100.0
            except (ValueError, TypeError):
                debt_to_equity = None

        current_ratio = info.get('currentRatio')
        roic = info.get('returnOnCapitalEmployed') or info.get('returnOnAssets') or info.get('returnOnEquity')

        # Dividends
        dividend_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate')
        dividend_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield')
        payout_ratio = info.get('payoutRatio')

        # FCF Trend - using already fetched future_cf
        fcf_history = []
        historic_fcf_growth = None
        try:
            cf = future_cf.result(timeout=2)
            if cf is not None and not cf.empty and 'Free Cash Flow' in cf.index:
                fcf_y = cf.loc['Free Cash Flow'].dropna().head(5).tolist()
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
        try:
            financials = future_fin.result(timeout=2)
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
            
        # Interest coverage & EBIT Margin
        interest_coverage = None
        ebit_margin = None
        try:
            financials = stock.financials
            if 'EBIT' in financials.index:
                ebit = financials.loc['EBIT'].dropna()
                
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

        # Historic Buyback Rate: avg annual reduction in shares outstanding (positive = buyback)
        historic_buyback_rate = None
        try:
            bs = stock.balance_sheet
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

        # Historical Trends for anchor charts (Revenue, Net Margin, FCF)
        historical_trends = []
        try:
            financials = stock.financials
            cashflow = stock.cashflow
            if not financials.empty and not cashflow.empty:
                # Find common columns, sort by date descending
                cols = list(set(financials.columns).intersection(cashflow.columns))
                cols.sort(reverse=True)
                years = cols[:10]  # Try to grab up to 10 years, though yfinance usually limits to 4 free
                
                for year in years:
                    rev = None
                    if 'Total Revenue' in financials.index:
                        rev_val = financials.loc['Total Revenue', year]
                        import pandas as pd
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
            "next_3y_rev_est": next_3y_rev_est
        }
    except Exception as e:
        print(f"Error fetching Yahoo Data for {ticker_symbol}: {e}")
        return None

def get_competitors_data(target_ticker: str, sector: str, industry: str, market_cap: float = 0, limit: int = 4) -> list:
    """
    Find relevant industry peers using multiple search strategies:
      1. Yahoo Finance v1 screener HTTP API (direct POST, industry filter)
      2. recommendationsbysymbol with strict same-industry validation
    Returns a list of dictionaries (from get_lightweight_company_data).
    """
    target_ticker = target_ticker.upper()
    target_tickers = []

    # Strategy 1: Yahoo Finance v1 screener via HTTP POST (Industry-based)
    if sector and industry:
        try:
            payload = {
                "offset": 0, "size": 10, "sortField": "intradaymarketcap", "sortType": "DESC", "quoteType": "EQUITY",
                "query": {"operator": "AND", "operands": [{"operator": "EQ", "operands": ["industry", industry]}]},
                "userId": "", "userIdType": "guid"
            }
            if market_cap and market_cap > 0:
                payload["query"]["operands"].append({
                    "operator": "BTWN",
                    "operands": ["intradaymarketcap", int(market_cap * 0.2), int(market_cap * 10)]
                })

            url = "https://query2.finance.yahoo.com/v1/finance/screener"
            headers = {
                'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                'Content-Type': 'application/json'
            }
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                sdata = r.json()
                sq = sdata.get('finance', {}).get('result', [{}])[0].get('quotes', [])
                for q in sq:
                    sym = (q.get('symbol') or '').upper()
                    if sym and sym != target_ticker and sym not in target_tickers:
                        target_tickers.append(sym)
                    if len(target_tickers) >= limit: break
        except Exception as e:
            print(f"Screener strategy failed: {e}")

    # Strategy 2: recommendationsbysymbol (Related tickers)
    if len(target_tickers) < limit:
        try:
            url = f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/{target_ticker}"
            headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                rdata = r.json()
                recs = rdata.get('finance', {}).get('result', [{}])[0].get('recommendedSymbols', [])
                candidates = [r['symbol'] for r in recs if r.get('symbol') and r['symbol'].upper() != target_ticker]
                
                if candidates:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(candidates), 8)) as exc:
                        futures = {exc.submit(lambda t: yf.Ticker(t).info, t): t for t in candidates}
                        for future in concurrent.futures.as_completed(futures):
                            try:
                                info = future.result()
                                sym = futures[future].upper()
                                sym_ind = info.get('industry', '')
                                if (not industry or sym_ind == industry) and sym not in target_tickers:
                                    target_tickers.append(sym)
                            except: pass
                            if len(target_tickers) >= limit: break
        except Exception as e:
            print(f"Recommendations strategy failed: {e}")

    # Strategy 3: Search Fallback (Industry/Sector based search)
    if len(target_tickers) < limit:
        try:
            query = industry or sector or target_ticker
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}"
            headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                sq = r.json().get('quotes', [])
                for q in sq:
                    sym = q.get('symbol')
                    if sym and sym.upper() != target_ticker and q.get('quoteType') == 'EQUITY' and sym not in target_tickers:
                        target_tickers.append(sym)
                    if len(target_tickers) >= limit: break
        except: pass

    target_tickers = target_tickers[:limit]

    # Fetch LIGHTWEIGHT data for validated peers (Parallel)
    peer_data = []
    if target_tickers:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(target_tickers)) as executor:
            futures = {executor.submit(get_lightweight_company_data, t): t for t in target_tickers}
            for future in concurrent.futures.as_completed(futures):
                try:
                    data = future.result()
                    if data:
                        peer_data.append(data)
                except Exception:
                    pass

    return peer_data

def get_lightweight_company_data(ticker_symbol: str):
    """Fetches a minimal set of data for competitor comparison."""
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        return {
            "ticker": ticker_symbol.upper(),
            "name": info.get('shortName') or info.get('longName') or ticker_symbol,
            "price": info.get('currentPrice') or info.get('regularMarketPrice'),
            "pe_ratio": info.get('trailingPE') or info.get('forwardPE')
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
        stock = yf.Ticker(ticker_symbol)
        info  = stock.info

        # ── Price Target ─────────────────────────────────────────────────────────
        target_mean  = info.get('targetMeanPrice')
        target_low   = info.get('targetLowPrice')
        target_high  = info.get('targetHighPrice')
        target_median = info.get('targetMedianPrice')
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        upside = ((target_mean - current_price) / current_price * 100) if (target_mean and current_price) else None

        # ── Analyst Recommendation ───────────────────────────────────────────────
        rec_key = info.get('recommendationKey', '')       # e.g. "buy", "strong_buy"
        rec_mean = info.get('recommendationMean')          # 1=Strong Buy … 5=Strong Sell
        num_analysts = info.get('numberOfAnalystOpinions')

        # Recommendation counts by category (from recommendations summary if available)
        rec_counts = {"strongBuy": 0, "buy": 0, "hold": 0, "sell": 0, "strongSell": 0}
        try:
            rec_df = stock.recommendations_summary          # DataFrame with period, strongBuy, buy, hold, sell, strongSell
            if rec_df is not None and not rec_df.empty:
                latest = rec_df.iloc[0]
                for k in rec_counts:
                    rec_counts[k] = int(latest.get(k, 0))
        except Exception:
            pass

        # ── EPS Estimates ────────────────────────────────────────────────────────
        eps_estimates = []
        try:
            import pandas as pd
            ef = stock.earnings_estimate   # index: 0q, +1q, 0y, +1y
            if ef is not None and not ef.empty:
                for period_idx, row in ef.iterrows():
                    avg = row.get('avg') if hasattr(row, 'get') else row.get('Avg')
                    low_e = row.get('low') if hasattr(row, 'get') else row.get('Low')
                    high_e = row.get('high') if hasattr(row, 'get') else row.get('High')
                    growth = row.get('growth') if hasattr(row, 'get') else row.get('Growth')
                    eps_estimates.append({
                        "period": str(period_idx),
                        "avg": float(avg) if avg is not None and not (isinstance(avg, float) and pd.isna(avg)) else None,
                        "low": float(low_e) if low_e is not None and not (isinstance(low_e, float) and pd.isna(low_e)) else None,
                        "high": float(high_e) if high_e is not None and not (isinstance(high_e, float) and pd.isna(high_e)) else None,
                        "growth": float(growth) if growth is not None and not (isinstance(growth, float) and pd.isna(growth)) else None,
                    })
        except Exception as e:
            print(f"[Analyst] EPS estimates error: {e}")

        # ── Revenue Estimates ─────────────────────────────────────────────────────
        rev_estimates = []
        try:
            import pandas as pd
            rf = stock.revenue_estimate
            if rf is not None and not rf.empty:
                for period_idx, row in rf.iterrows():
                    avg = row.get('avg') if hasattr(row, 'get') else None
                    low_r = row.get('low') if hasattr(row, 'get') else None
                    high_r = row.get('high') if hasattr(row, 'get') else None
                    growth = row.get('growth') if hasattr(row, 'get') else None
                    rev_estimates.append({
                        "period": str(period_idx),
                        "avg": float(avg) if avg is not None and not (isinstance(avg, float) and pd.isna(avg)) else None,
                        "low": float(low_r) if low_r is not None and not (isinstance(low_r, float) and pd.isna(low_r)) else None,
                        "high": float(high_r) if high_r is not None and not (isinstance(high_r, float) and pd.isna(high_r)) else None,
                        "growth": float(growth) if growth is not None and not (isinstance(growth, float) and pd.isna(growth)) else None,
                    })
        except Exception as e:
            print(f"[Analyst] Revenue estimates error: {e}")

        # ── EPS Surprise History (last 4 quarters) ────────────────────────────────
        eps_history = []
        try:
            import pandas as pd
            eh = stock.earnings_history
            if eh is not None and not eh.empty:
                for _, row in eh.tail(4).iterrows():
                    date_val = row.get('quarter') if hasattr(row, 'get') else None
                    eps_act = row.get('epsActual') if hasattr(row, 'get') else None
                    eps_est = row.get('epsEstimate') if hasattr(row, 'get') else None
                    surprise = row.get('epsDifference') if hasattr(row, 'get') else None
                    surprise_pct = row.get('surprisePercent') if hasattr(row, 'get') else None
                    eps_history.append({
                        "quarter": str(date_val) if date_val else None,
                        "actual":   float(eps_act) if eps_act is not None and not (isinstance(eps_act, float) and pd.isna(eps_act)) else None,
                        "estimate": float(eps_est) if eps_est is not None and not (isinstance(eps_est, float) and pd.isna(eps_est)) else None,
                        "surprise": float(surprise) if surprise is not None and not (isinstance(surprise, float) and pd.isna(surprise)) else None,
                        "surprise_pct": float(surprise_pct) if surprise_pct is not None and not (isinstance(surprise_pct, float) and pd.isna(surprise_pct)) else None,
                    })
        except Exception as e:
            print(f"[Analyst] EPS history error: {e}")

        # ── EPS growth from estimates ─────────────────────────────────────────────
        # Try to find a stable forward growth rate to match calculations
        eps_forward_growth = info.get('earningsGrowth') # fallback
        if eps_estimates:
            # Prefer +1y growth which is what users usually see in the table
            for est in eps_estimates:
                if est['period'] == '+1y' and est['growth'] is not None:
                    eps_forward_growth = est['growth']
                    break

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
            "eps_5yr_growth": eps_forward_growth, # Renamed or repurposed for consistency
            "eps_estimates":  eps_estimates,
            "rev_estimates":  rev_estimates,
            "eps_history":    eps_history
        }

    except Exception as e:
        print(f"[Analyst] Data fetch failed for {ticker_symbol}: {e}")
        return {"ticker": ticker_symbol.upper(), "error": str(e)}
