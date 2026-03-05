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
        info = stock.info
        
        # If it's a name instead of a ticker, Yahoo might return empty/basic info. Fallback to search query.
        if not info or ('shortName' not in info and 'currentPrice' not in info and 'regularMarketPrice' not in info):
            resolved = resolve_company_name(ticker_symbol)
            if resolved and resolved != ticker_symbol:
                ticker_symbol = resolved
                stock = yf.Ticker(ticker_symbol)
                info = stock.info
        
        # Basic Price and Identifying Info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        name = info.get('shortName', ticker_symbol)
        sector = info.get('sector')
        industry = info.get('industry')
        
        # Valuation Multiples & EPS
        trailing_eps = info.get('trailingEps') or info.get('epsTrailingTwelveMonths')
        forward_eps = info.get('forwardEps')
        pe_ratio = info.get('trailingPE')
        forward_pe = info.get('forwardPE')
        ps_ratio = info.get('priceToSalesTrailing12Months')
        
        # Calculate next year growth using NASDAQ explicitly as requested
        eps_growth = get_nasdaq_earnings_growth(ticker_symbol, trailing_eps)
        
        # Fallback to Yahoo if Nasdaq fails
        if eps_growth is None:
            eps_growth = info.get('earningsGrowth')
            if not eps_growth and forward_eps and trailing_eps and trailing_eps > 0:
                eps_growth = (forward_eps - trailing_eps) / trailing_eps
            elif not eps_growth:
                eps_growth = info.get('revenueGrowth', 0.05)
            
        # Calculate PEG explicitly based on next year's growth so it always aligns with user request
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
                debt_to_equity = float(debt_to_equity) / 100.0  # Yahoo returns this as a percentage e.g., 57.26 -> 0.57x
            except (ValueError, TypeError):
                debt_to_equity = None

        current_ratio = info.get('currentRatio')
        roic = info.get('returnOnCapitalEmployed') or info.get('returnOnAssets') or info.get('returnOnEquity')

        # Dividends for DDM
        dividend_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate')
        dividend_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield')
        payout_ratio = info.get('payoutRatio')

        # FCF Trend (past 5 years newest to oldest)
        fcf_history = []
        historic_fcf_growth = None
        try:
            cf = stock.cashflow
            if 'Free Cash Flow' in cf.index:
                fcf_y = cf.loc['Free Cash Flow'].dropna().head(5).tolist()
                fcf_history = fcf_y[:3]  # keep 3 for scoring compatibility
                
                if len(fcf_y) >= 2:
                    yoy_rates = []
                    for i in range(len(fcf_y)-1):
                        new_val = fcf_y[i]
                        old_val = fcf_y[i+1]
                        if old_val != 0:
                            yoy_rates.append((new_val - old_val) / abs(old_val))
                    if yoy_rates:
                        historic_fcf_growth = sum(yoy_rates) / len(yoy_rates)
        except Exception:
            pass
            
        # Historic EPS growth (Approximate 5 years Average YoY)
        historic_eps_growth = None
        try:
            financials = stock.financials
            if 'Basic EPS' in financials.index or 'Diluted EPS' in financials.index:
                eps_row = financials.loc['Diluted EPS'] if 'Diluted EPS' in financials.index else financials.loc['Basic EPS']
                eps_vals = eps_row.dropna().head(5).tolist()
                if len(eps_vals) >= 2:
                    yoy_rates = []
                    for i in range(len(eps_vals)-1):
                        new_val = eps_vals[i]
                        old_val = eps_vals[i+1]
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

def get_competitors_data(ticker: str, sector: str, industry: str, market_cap: float = 0, limit: int = 4):
    target_ticker = ticker.upper()
    target_tickers = []
    
    # 1. Dynamic BFS using Yahoo recommendationsbysymbol if parameters allow
    if industry and market_cap and market_cap > 0:
        queue = [target_ticker]
        seen = {target_ticker}
        queries = 0
        max_queries = 25 # prevent infinite loop or extreme delays
        
        while queue and len(target_tickers) < limit and queries < max_queries:
            current_ticker = queue.pop(0)
            queries += 1
            
            try:
                url = f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/{current_ticker}"
                req = urllib.request.Request(url, headers={'User-Agent': get_random_agent()})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    recs = data.get('finance', {}).get('result', [{}])[0].get('recommendedSymbols', [])
                    new_symbols = [r['symbol'] for r in recs if r.get('symbol') and r['symbol'] not in seen]
            except Exception:
                new_symbols = []
                
            for symbol in new_symbols:
                seen.add(symbol)
                queue.append(symbol)
                
            # Process in concurrent batches to check info faster
            if new_symbols:
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(new_symbols), 10)) as exc:
                    futures = {exc.submit(lambda t: yf.Ticker(t).info, t): t for t in new_symbols}
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            info = future.result()
                            sym = futures[future]
                            sym_industry = info.get('industry')
                            sym_mc = info.get('marketCap', 0)
                            
                            if sym_industry == industry and (market_cap * 0.2) <= sym_mc <= (market_cap * 5.0):
                                if sym not in target_tickers and sym != target_ticker:
                                    target_tickers.append(sym)
                        except Exception:
                            pass
                            
            if len(target_tickers) >= limit:
                break
                
        target_tickers = target_tickers[:limit]

    # 2. Fallback to hardcoded list if the dynamic crawler fails to find enough peers
    if len(target_tickers) < limit:
        hardcoded_peers = {
            "SOFI": ["UPST", "AFRM", "NU", "HOOD"],
            "PLTR": ["SNOW", "DDOG", "NET", "CRWD"],
            "FISV": ["V", "MA", "PYPL", "GPN"],
            "FI": ["V", "MA", "PYPL", "GPN"],
            "TSLA": ["RIVN", "LCID", "F", "GM"],
            "AMZN": ["MSFT", "GOOGL", "META", "AAPL"]
        }
        peers_map = {
            "Technology": ["MSFT", "AAPL", "GOOGL", "META"],
            "Software - Infrastructure": ["ADBE", "CRM", "INTU", "ORCL"],
            "Software - Application": ["ADBE", "CRM", "INTU", "WDAY"],
            "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD"],
            "Financial Services": ["JPM", "BAC", "V", "MA"],
            "Healthcare": ["JNJ", "UNH", "LLY", "ABBV"]
        }
        fallback_tickers = hardcoded_peers.get(target_ticker)
        if not fallback_tickers:
            fallback_tickers = peers_map.get(industry, peers_map.get(sector, ["MSFT", "AAPL"]))
        
        for ft in fallback_tickers:
            if ft != target_ticker and ft not in target_tickers:
                target_tickers.append(ft)
        target_tickers = target_tickers[:limit]
        
    peer_data = []
    # 3. Fetch full data for the validated competitors
    if target_tickers:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(target_tickers)) as executor:
            futures = {executor.submit(get_company_data, t): t for t in target_tickers}
            for future in concurrent.futures.as_completed(futures):
                try:
                    data = future.result()
                    if data:
                        peer_data.append(data)
                except Exception as e:
                    print(f"Error fetching full data for competitor {futures[future]}: {e}")
                    
    return peer_data

def get_market_averages():
    """
    Returns S&P 500 P/E metrics using SPY as a proxy.
    """
    try:
        spy = yf.Ticker("SPY")
        info = spy.info
        return {
            "trailing_pe": info.get('trailingPE'),
            "forward_pe": info.get('forwardPE') or info.get('trailingPE')
        }
    except Exception as e:
        print(f"Error fetching SPY market average: {e}")
        return {
            "trailing_pe": 25.0, # Fallback S&P avg
            "forward_pe": 21.0
        }
