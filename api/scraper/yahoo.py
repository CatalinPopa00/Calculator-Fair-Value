import yfinance as yf
import os
import json
import datetime
import urllib.request
import urllib.parse
import concurrent.futures
import time
import random
import requests
import pandas as pd
import re
try:
    from ..utils.kv import kv_get, kv_set
except ImportError:
    try:
        from api.utils.kv import kv_get, kv_set
    except ImportError:
        def kv_get(k): return None
        def kv_set(k, v, ex=None): return False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

# Robust Insights File Discovery
def _find_insights_file():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "data", "company_insights.json")
    if os.path.exists(path):
        return path
    # Fallback to current working directory discovery
    cwd_path = os.path.join(os.getcwd(), "api", "data", "company_insights.json")
    if os.path.exists(cwd_path):
        return cwd_path
    return path

INSIGHTS_FILE = _find_insights_file()

def normalize_growth(val):
    """Ensure growth rate is a decimal (e.g., 0.05 for 5%) even if source gives 5.0"""
    if val is None: return None
    try:
        f_val = float(val)
        # If absolute value > 1.0 (e.g. 7.56 or 756), it's likely a percentage
        # Unless it's truly massive (756x growth), but for financial metrics > 2.0 (200%) usually needs correction
        if abs(f_val) > 2.0:
            return f_val / 100.0
        return f_val
    except:
        return None

def find_idx(df, target):
    """Case-insensitive index lookup for pandas DataFrames."""
    if df is None or df.empty: return None
    target_lower = str(target).lower().strip()
    for idx in df.index:
        if str(idx).lower().strip() == target_lower: return idx
    return None

def find_nearest_col(df, target_date, max_days=7):
    """Finds the column index in df that most closely matches target_date within max_days."""
    if df is None or df.empty or target_date is None:
        return None
    # Try exact match
    if target_date in df.columns:
        return target_date
    # Normalize target_date to Timestamp if it is a string
    if isinstance(target_date, str):
        try: target_date = pd.to_datetime(target_date)
        except: return None
    
    best_col = None
    min_delta = None
    
    for col in df.columns:
        try:
            col_ts = pd.to_datetime(col)
            delta = abs((col_ts - target_date).days)
            if delta <= max_days:
                if min_delta is None or delta < min_delta:
                    min_delta = delta
                    best_col = col
        except: continue
    return best_col

def get_random_agent():
    return random.choice(USER_AGENTS)

# Global cache for market averages (SPY) with 1-hour TTL
_market_cache = {"data": None, "timestamp": 0}
_risk_free_cache = {"rate": None, "timestamp": 0}
_peer_info_cache = {} # Global memory cache for peer info (1-hour TTL)

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

def get_fx_rate(info: dict) -> float:
    """Detects currency mismatch and fetches dynamic FX rate from Yahoo."""
    # Hard-stop for known USD tickers that shouldn't fluctuate
    if info.get('symbol') in ['META', 'NVDA', 'AAPL', 'MSFT', 'GOOG', 'GOOGL', 'AMZN', 'TSLA', 'FDS']:
        return 1.0

    financial_currency = info.get('financialCurrency', 'USD')
    price_currency = info.get('currency', 'USD')
    
    if not financial_currency or not price_currency or financial_currency == price_currency:
        return 1.0
        
    try:
        # Construct symbol (e.g., DKKUSD=X)
        fx_symbol = f"{financial_currency}{price_currency}=X"
        fx_ticker = yf.Ticker(fx_symbol)
        # Fetch 1d history to get the most recent Close
        fx_hist = fx_ticker.history(period="1d")
        if not fx_hist.empty:
            rate = float(fx_hist['Close'].iloc[-1])
            # print(f"DEBUG: FX Rate for {fx_symbol} detected: {rate}")
            return rate
    except Exception as e:
        print(f"Error fetching FX Rate for {info.get('symbol', 'Unknown')}: {e}")
        
    return 1.0

def get_nasdaq_comprehensive_estimates(ticker: str) -> dict:
    """ Fetches yearly and quarterly EPS AND Revenue estimates from Nasdaq in parallel. """
    ticker = ticker.upper()
    cache_key = f"nq_comp_v2_{ticker}"
    cached = kv_get(cache_key)
    if cached: return cached

    results = {"yearly_eps": [], "quarterly_eps": [], "yearly_rev": [], "quarterly_rev": []}
    
    def fetch_url(url_type, t_sym):
        endpoint = "earnings-forecast" if url_type == "eps" else "revenue-forecast"
        try:
            url = f'https://api.nasdaq.com/api/analyst/{t_sym}/{endpoint}'
            headers = {'User-Agent': get_random_agent()}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=7) as response:
                return json.loads(response.read())
        except: return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_eps = executor.submit(fetch_url, "eps", ticker)
        future_rev = executor.submit(fetch_url, "rev", ticker)
        
        eps_data = future_eps.result()
        rev_data = future_rev.result()
        
        if eps_data:
            results["yearly_eps"] = eps_data.get('data', {}).get('yearlyForecast', {}).get('rows', [])
            results["quarterly_eps"] = eps_data.get('data', {}).get('quarterlyForecast', {}).get('rows', [])
        if rev_data:
            results["yearly_rev"] = rev_data.get('data', {}).get('yearlyForecast', {}).get('rows', [])
            results["quarterly_rev"] = rev_data.get('data', {}).get('quarterlyForecast', {}).get('rows', [])

    if results["yearly_eps"] or results["yearly_rev"]:
        kv_set(cache_key, results, ex=600) # 10 mins cache
    return results

def get_nasdaq_historical_eps(ticker: str) -> list:
    """Fetch quarterly Adjusted (Non-GAAP) EPS from Nasdaq Surprise API."""
    try:
        url = f"https://api.nasdaq.com/api/company/{ticker}/earnings-surprise"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.nasdaq.com',
            'Referer': f'https://www.nasdaq.com/market-activity/stocks/{ticker.lower()}/earnings'
        }
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            chart = data.get('data', {}).get('chart', [])
            result = []
            for item in chart:
                try:
                    # 'x' is timestamp in seconds, 'y' is actual EPS
                    dt = datetime.datetime.fromtimestamp(int(item['x']), tz=datetime.timezone.utc)
                    eps = float(item['y'])
                    result.append({"date": dt, "eps": eps})
                except: continue
            return result
    except Exception as e:
        print(f"Error fetching Nasdaq Historical Adj EPS for {ticker}: {e}")
    return []

def safe_nasdaq_float(val):
    if val is None or str(val).strip() == "" or str(val).upper() == "N/A": 
        return None
    if isinstance(val, (int, float)): return float(val)
    try:
        clean_val = str(val).replace('$', '').replace(',', '').strip()
        if not clean_val: return None
        return float(clean_val)
    except: return None

def get_nasdaq_earnings_growth(ticker: str, trailing_eps: float) -> float:
    """
    Fetches multi-year forward earnings growth estimates from Nasdaq.
    Targets the 3-year horizon (e.g., 2027-2029) to calculate a CAGR.
    """
    if not trailing_eps or trailing_eps <= 0:
        return None
    try:
        # Optimization: Use the comprehensive fetcher
        nq_data = get_nasdaq_comprehensive_estimates(ticker)
        rows = nq_data.get("yearly_eps", [])
        if not rows: return None
        
        # Start from Trailing EPS (T0) as the base
        base_eps = trailing_eps
        
        # Target the 3rd year in the forecast if available (T3), else the furthest available.
        target_idx = min(len(rows) - 1, 2) # Target up to T3 (rows[2])
        raw_val = rows[target_idx].get('consensusEPSForecast', 0)
        target_eps = safe_nasdaq_float(raw_val)
        n_years = target_idx + 1 # Years from T0 to Target
        
        # Floor the base at 0.10 if it's positive but tiny
        effective_base = max(base_eps, 0.10) if base_eps > 0 else base_eps
        
        if target_eps > 0 and n_years > 0 and effective_base > 0:
            # CAGR = (End/Start)^(1/Years) - 1
            return (target_eps / effective_base) ** (1 / n_years) - 1

    except Exception as e:
        print(f"Error fetching Nasdaq growth for {ticker}: {e}")
    return None

def get_nasdaq_actual_eps(ticker: str) -> float:
    """
    Fetches the actual Adjusted (Non-GAAP) EPS for the last 4 quarters from Nasdaq.
    Sums them to provide a more accurate 'Trailing EPS' for companies with large GAAP vs Non-GAAP gaps.
    """
    try:
        url = f'https://api.nasdaq.com/api/company/{ticker.upper()}/earnings-surprise'
        req = urllib.request.Request(url, headers={'User-Agent': get_random_agent()})
        with urllib.request.urlopen(req, timeout=3) as response:
            raw_data = response.read()
            data = json.loads(raw_data)
            
        rows = data.get('data', {}).get('earningsSurpriseTable', {}).get('rows', [])
        if rows:
            total_eps = 0.0
            # Sum the last 4 reported quarters
            count = 0
            for row in rows[:4]:
                # 'eps' is the actual reported EPS in the surprise table
                val_str = row.get('eps') or row.get('actualEPS')
                if val_str:
                    try:
                        total_eps += float(val_str)
                        count += 1
                    except ValueError:
                        continue
            
            if count >= 3: # Require at least 3 quarters for a valid sum
                # v70: Scale to full year (4 quarters) if one is missing
                return (total_eps / count) * 4.0
    except Exception as e:
        print(f"Error fetching Nasdaq Actual EPS for {ticker}: {e}")
    return None

def calculate_historic_pe(stock, financials, fx_rate=1.0):
    """Calculates a 5-year average P/E ratio by matching annual EPS with historical prices."""
    if financials is None or financials.empty:
        return None
    
    try:
        # Prefer Diluted EPS, fallback to Basic EPS
        eps_row = None
        if 'Diluted EPS' in financials.index:
            eps_row = financials.loc['Diluted EPS']
        elif 'Basic EPS' in financials.index:
            eps_row = financials.loc['Basic EPS']
        
        if eps_row is None:
            return None
        
        # Take up to 5 years (latest first)
        eps_values = eps_row.dropna().head(5)
        if eps_values.empty:
            return None
        
        # Fetch 5-year history once
        try:
            hist_5y = stock.history(period="5y")
            if not hist_5y.empty and hasattr(hist_5y.index, 'tz_localize') and hist_5y.index.tz is not None:
                hist_5y.index = hist_5y.index.tz_localize(None)
        except Exception:
            return None

        pe_ratios = []
        for date, eps in eps_values.items():
            if eps <= 0: # Skip negative/zero EPS for P/E average
                continue
            
            try:
                # Find closest date in hist_5y
                if hasattr(date, 'tz_localize') and date.tz is not None:
                    target_date = date.tz_localize(None)
                else:
                    target_date = date
                    
                # Get window of +/- 10 days around target_date
                window = hist_5y[(hist_5y.index >= target_date - pd.Timedelta(days=10)) & 
                                 (hist_5y.index <= target_date + pd.Timedelta(days=10))]
                
                if not window.empty:
                    # Get the price closest to target date
                    valid_dates = window[window.index <= target_date]
                    if not valid_dates.empty:
                        price = float(valid_dates['Close'].iloc[-1])
                    else:
                        price = float(window['Close'].iloc[0])
                        
                    # CRITICAL: Scale eps by fx_rate to get P/E in USD terms.
                    pe_ratios.append(price / (eps * fx_rate))
            except Exception:
                continue
                
        if not pe_ratios:
            return None
            
        return sum(pe_ratios) / len(pe_ratios)
    except Exception as e:
        print(f"Error calculating Historic PE: {e}")
        return None

def get_period_labels(ticker_info: dict) -> dict:
    """
    Returns a mapping for relative period codes based on the company's fiscal year.
    Standardizes on 'FY 20XX' and relative quarters.
    """
    try:
        now = datetime.datetime.now()
        lfy_ts = ticker_info.get('lastFiscalYearEnd')
        if not lfy_ts:
            current_fy = now.year if now.month <= 12 else now.year + 1
        else:
            lfy_dt = datetime.datetime.fromtimestamp(lfy_ts)
            fy_end_month = lfy_dt.month
            # We are currently in the fiscal year that ends NEXT.
            # If our current month is past the last fiscal end month, the next end is next year.
            if now.month > fy_end_month:
                current_fy = now.year + 1
            else:
                current_fy = now.year

        return {
            "0q": "Current Qtr",
            "+1q": "Next Qtr",
            "+2q": "Q3 Est.",
            "+3q": "Q4 Est.",
            "0y": f"FY {current_fy}",
            "+1y": f"FY {current_fy + 1}"
        }
    except:
        curr_year = datetime.datetime.now().year
        return {
            "0q": "Current Qtr", "+1q": "Next Qtr",
            "0y": f"FY {curr_year}", "+1y": f"FY {curr_year + 1}"
        }

def resolve_company_name(query: str) -> str:
    """Uses Yahoo Finance search to resolve a company name to a ticker symbol."""
    for attempt in range(3):
        try:
            url = f'https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}'
            req = urllib.request.Request(url, headers={'User-Agent': get_random_agent()})
            with urllib.request.urlopen(req, timeout=3) as response:
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
    """Uses Yahoo Finance search to get an autocomplete list (Multi-host & Robust)."""
    search_query = query.strip()
    if not search_query:
        return []

    # Try both query1 and query2 for robustness
    hosts = ["query2.finance.yahoo.com", "query1.finance.yahoo.com"]
    
    # High-quality headers mimicking a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/lookup",
        "Cache-Control": "no-cache"
    }

    last_error = None
    for host in hosts:
        try:
            # quotesCount=25 gives us more buffer for short queries
            # newsCount=0, enableFuzzyQuery=true to catch MSFT for 'm' etc.
            url = f"https://{host}/v1/finance/search?q={urllib.parse.quote(search_query)}&quotesCount=25&newsCount=0&enableFuzzyQuery=true"
            
            response = requests.get(url, headers=headers, timeout=4)
            if response.status_code == 200:
                data = response.json()
                quotes = data.get("quotes", [])
                
                # Filtering logic
                valid_quotes = []
                for q in quotes:
                    symbol = q.get("symbol", "")
                    q_type = q.get("quoteType", "").upper()
                    
                    # EQUITY or ETF, and NO dots (US markets only)
                    if q_type in ["EQUITY", "ETF"] and "." not in symbol:
                        valid_quotes.append({
                            "ticker": symbol.upper(),
                            "name": q.get("shortname") or q.get("longname") or symbol,
                            "exchange": q.get("exchDisp") or "N/A"
                        })
                
                # Re-order for exact match priority
                exact_match = None
                others = []
                
                query_lower = search_query.lower()
                for v in valid_quotes:
                    if v["ticker"].lower() == query_lower and exact_match is None:
                        exact_match = v
                    else:
                        others.append(v)
                
                final_results = ([exact_match] if exact_match else []) + others
                return final_results[:6]
            
            elif response.status_code == 429:
                print(f"Yahoo Search Rate Limited (429) on {host}")
                continue
                
        except Exception as e:
            last_error = e
            print(f"Yahoo Search Error on {host}: {str(e)}")
            continue

    if last_error:
        print(f"Search failed on all hosts. Last error: {last_error}")
    return []

def get_company_synthesis(ticker: str, info: dict) -> str:
    """
    Returns a concise, analytical synthesis of the company in Romanian.
    Checks the local insights database first, falls back to a structured summary.
    """
    ticker_upper = ticker.upper()
    
    # 1. Check Knowledge Base
    try:
        if os.path.exists(INSIGHTS_FILE):
            with open(INSIGHTS_FILE, "r", encoding="utf-8") as f:
                insights = json.load(f)
                if ticker_upper in insights:
                    return insights[ticker_upper]
    except Exception as e:
        print(f"Error loading insights file: {e}")

    # 2. Professional Fallback (Structured Romanian Summary)
    sector = info.get('sector', 'N/A')
    industry = info.get('industry', 'N/A')
    name = info.get('longName') or ticker_upper
    
    # Simple heuristic-based analytical synthesis
    if sector != 'N/A' and industry != 'N/A':
        return f"{name} este o entitate majoră în sectorul {sector}, operând în industria {industry}. Compania își generează veniturile prin furnizarea de soluții și produse integrate către o bază globală de clienți. Avantajul său competitiv se bazează pe poziționarea strategică în piață și pe capacitatea de inovare continuă în domeniul de activitate."
    
    return f"Sinteză indisponibilă. {name} activează în sectorul financiar global, generând fluxuri de numerar prin operațiuni comerciale specifice industriei sale. Detalii analitice despre fluxurile de venituri și avantajul competitiv sunt în curs de procesare."

def get_company_data(ticker_symbol: str, fast_mode: bool = False):
    """
    Fetches comprehensive data from Yahoo Finance + Finnhub fallbacks for resilience.
    """
    # Initialize all potential variables to prevent UnboundLocalError
    name = ticker_symbol
    sector = "N/A"
    industry = "N/A"
    current_price = None
    data_source = "unknown"
    trailing_eps = 0
    adjusted_eps = 0
    forward_eps = 0
    pe_ratio = None
    forward_pe = None
    ps_ratio = None
    fwd_ps = None
    eps_growth = 0.05
    eps_growth_period = "N/A"
    fcf = None
    fcf_history = []
    operating_cashflow = None
    market_cap = 0
    shares_outstanding = None
    total_cash = 0
    total_debt = 0
    debt_to_equity = None
    current_ratio = None
    roic = None
    roe = None
    roa = None
    interest_coverage = None
    price_to_book = None
    revenue = 0
    revenue_growth_val = None
    earnings_growth_val = None
    next_3y_rev_est = None
    ebit_margin = None
    dividend_yield = None
    dividend_rate = None
    dividend_streak = 0
    dividend_cagr_5y = None
    payout_ratio = None
    historic_eps_growth = None
    historic_fcf_growth = None
    historic_buyback_rate = None
    red_flags = []
    historical_trends = []
    historical_data = {
        "years": [], "revenue": [], "eps": [], "fcf": [], "shares": []
    }
    peg_ratio = None

    try:
        # --- ATTEMPT 1: yf.Ticker.info (Primary) ---
        stock = yf.Ticker(ticker_symbol)
        
        # Parallelize data fetching
        try:
            info = stock.info
            if not info: info = {}
        except Exception:
            info = {}

        # Identifying Info
        name = info.get('shortName', ticker_symbol)
        sector = info.get('sector')
        industry = info.get('industry')

        # --- PRICE DISCOVERY (Authoritative Sequence + Scale Sanity) ---
        # The 'Anchor' is the last known good trading price from the info summary
        anchor_price = info.get('regularMarketPrice') or info.get('currentPrice')
        prev_close = info.get('regularMarketPreviousClose') or anchor_price
        current_price = None
        data_source = "yahoo_fast_info"

        # Attempt 1: Fast Info (Modern, Live)
        try:
            cf_val = stock.fast_info.get('last_price')
            if cf_val and cf_val > 0:
                # Sanity Check: If FastInfo differs from PrevClose by > 50%, it's likely a split-error (e.g. ADBE)
                if prev_close and (cf_val < prev_close * 0.7 or cf_val > prev_close * 1.3):
                    # Discrepancy detected, favor the Anchor if it's closer to PrevClose
                    if anchor_price and abs(anchor_price/prev_close - 1) < abs(cf_val/prev_close - 1):
                        current_price = float(anchor_price)
                        data_source = "yahoo_info_anchor"
                    else:
                        current_price = float(cf_val)
                else:
                    current_price = float(cf_val)
        except: pass
        
        # Attempt 2: History (Verified Close)
        if current_price is None:
            try:
                hist = stock.history(period="1d")
                if not hist.empty:
                    h_val = float(hist['Close'].iloc[-1])
                    # Sanity Check against PrevClose
                    if prev_close and (h_val < prev_close * 0.7 or h_val > prev_close * 1.3):
                         current_price = float(anchor_price) if anchor_price else h_val
                         data_source = "yahoo_info_anchor"
                    else:
                        current_price = h_val
                        data_source = "yahoo_history"
            except: pass

        # Attempt 3: Direct Chart API (v8)
        if current_price is None:
            try:
                c_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_symbol}?interval=1d&range=1d"
                headers = {'User-Agent': get_random_agent()}
                c_resp = requests.get(c_url, headers=headers, timeout=5).json()
                meta = c_resp.get('chart', {}).get('result', [{}])[0].get('meta', {})
                if meta.get('regularMarketPrice'):
                    current_price = meta['regularMarketPrice']
                    data_source = "yahoo_chart_v8"
            except: pass

        # Final Fallback
        if current_price is None:
            current_price = anchor_price
            data_source = "yahoo_info_fallback"

        # 0. FX Normalization (Dynamic conversion for ADRs)
        fx_rate = get_fx_rate(info)

        # FY End Month extraction (v63: Fixed for Non-GAAP Aggregation)
        lfy_ts = info.get('lastFiscalYearEnd')
        fy_end_month = 12 # Default
        if lfy_ts:
            try:
                # Use a safer conversion for timestamp
                fy_end_month = datetime.datetime.fromtimestamp(lfy_ts).month
            except Exception:
                pass

        # Start background fetches while processing info
        executor = None
        if not fast_mode:
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
            future_nasdaq_cagr = executor.submit(get_nasdaq_earnings_growth, ticker_symbol, info.get('trailingEps'))
            future_nasdaq_actual = executor.submit(get_nasdaq_actual_eps, ticker_symbol)
            future_est = executor.submit(lambda: getattr(stock, 'earnings_estimate', None))
            future_growth_est = executor.submit(lambda: getattr(stock, 'growth_estimates', None))
            future_fin = executor.submit(lambda: getattr(stock, 'financials', None))

        # Valuation Multiples & EPS (Initial from info tags - will be recalibrated after financials load)
        trailing_eps = (info.get('trailingEps') or info.get('epsTrailingTwelveMonths', 0))
        adjusted_eps = trailing_eps  # Will be updated to Non-GAAP after financials load
        forward_eps = (info.get('forwardEps') or 0)
        pe_ratio = info.get('trailingPE')  # Initial from info, recalculated later
        if not pe_ratio and current_price and trailing_eps and trailing_eps > 0:
            pe_ratio = current_price / trailing_eps
        forward_pe = info.get('forwardPE')
        ps_ratio = info.get('priceToSalesTrailing12Months')
        revenue_growth_val = info.get('revenueGrowth')
        earnings_growth_val = info.get('earningsGrowth')
        
        eps_growth = None
        eps_growth_period = None

        # 1. Try YF growth_estimates (Analysis tab - Next 5 Years) - TOP PRIORITY for PEG
        eps_growth_5y_consensus = None
        if not fast_mode and executor is not None:
            try:
                ge = future_growth_est.result(timeout=2)
                if ge is not None and not (hasattr(ge, 'empty') and ge.empty):
                    # Find 'Next 5 Years' in index
                    idx = find_idx(ge, 'Next 5 Years')
                    if idx:
                        val = ge.loc[idx, ge.columns[0]]
                        if val is not None and not pd.isna(val):
                            eps_growth_5y_consensus = float(val)
                            eps_growth = eps_growth_5y_consensus
                            eps_growth_period = "Next 5 Years (Consensus)"
            except Exception:
                pass

        # 2. Try YF earnings_estimate (Forward Years) - SECOND PRIORITY
        if eps_growth is None and not fast_mode and executor is not None:
            try:
                ef = future_est.result(timeout=2)
                if ef is not None and not (hasattr(ef, 'empty') and ef.empty):
                    # pick healthiest forward year (+5y -> +1y -> 0y)
                    g_5y = ef.loc['+5y'].get('growth') if '+5y' in ef.index else None
                    g_1y = ef.loc['+1y'].get('growth') if '+1y' in ef.index else None
                    
                    labels = get_period_labels(info)
                    
                    if g_5y is not None:
                        eps_growth = float(g_5y)
                        eps_growth_period = labels.get('+5y', 'Next 5 Years (Est)')
                    elif g_1y is not None:
                        # Only use +1y if it is sane (positive) OR if we have no other choice
                        eps_growth = float(g_1y)
                        eps_growth_period = labels.get('+1y', 'Next Year (Est)')
            except Exception:
                pass

        # 3. Try Nasdaq growth (fallback)
        nasdaq_growth_3y = None
        nasdaq_actual_eps = None
        if not fast_mode and executor is not None:
            try:
                nasdaq_growth_3y = future_nasdaq_cagr.result(timeout=5)
                nasdaq_actual_eps = future_nasdaq_actual.result(timeout=5)
            except Exception:
                pass

        # Detect Nasdaq Actual (Non-GAAP)
        if nasdaq_actual_eps is not None:
            # Store separately instead of overwriting the main trailing_eps
            # This allow the UI to show the GAAP value the user expects from Yahoo summary
            adjusted_eps = nasdaq_actual_eps
        else:
            adjusted_eps = trailing_eps

        # --- GROWTH SELECTION (USER REQUESTED PRIORITY: NASDAQ 3Y) ---
        if nasdaq_growth_3y and nasdaq_growth_3y > 0:
            eps_growth = nasdaq_growth_3y
            eps_growth_period = "3Y CAGR EPS (Nasdaq)"
        
        # 1. Fallback to YF growth_estimates (Analysis tab - Next 5 Years) if Nasdaq missing
        if eps_growth is None and eps_growth_5y_consensus:
            eps_growth = eps_growth_5y_consensus
            eps_growth_period = "Next 5 Years (Consensus)"
            
        # 3. Last resort: strictly use provided growth or 0
        if eps_growth is None:
            eg_val = info.get('earningsGrowth')
            if eg_val and eg_val > 0:
                eps_growth = eg_val
                eps_growth_period = "Trailing Growth"
            else:
                # Use revenue growth if explicitly provided, else 0 (No Implied PE deduction)
                eps_growth = info.get('revenueGrowth', 0)
                eps_growth_period = "Revenue Growth Proxy" if eps_growth > 0 else "None"
            
        # Financials for DCF & Margins (Wait for results)
        financials = None
        cashflow = None
        bs = None
        q_bs = None
        q_financials = None
        q_cashflow = None
        dividends_raw = pd.Series()

        if not fast_mode:
            try:
                if executor is not None:
                    financials = future_fin.result(timeout=5)
                else: financials = getattr(stock, 'financials', {})
            except Exception:
                financials = {}
            if financials is None or (hasattr(financials, 'empty') and financials.empty):
                financials = {}

            try: cashflow = getattr(stock, 'cashflow', {})
            except Exception: cashflow = {}
            if cashflow is None or (hasattr(cashflow, 'empty') and cashflow.empty):
                cashflow = {}

            try: bs = getattr(stock, 'balance_sheet', {})
            except Exception: bs = {}
            if bs is None or (hasattr(bs, 'empty') and bs.empty):
                bs = {}
            
            if executor is not None:
                executor.shutdown(wait=False)

            q_bs = stock.quarterly_balance_sheet
            
            # Massive speedups: No longer awaiting qfin, qcf, or heavy dividends histories.

        # ── TRUE SHARES OUTSTANDING (Fix for Dual-Class) ──
        shares_outstanding = None
        if financials is not None and not financials.empty:
            for k in ['Diluted Average Shares', 'Basic Average Shares']:
                idx = find_idx(financials, k)
                if idx:
                    try:
                        val = float(financials.loc[idx].iloc[0])
                        if val > 0:
                            shares_outstanding = val
                            break
                    except: pass
        if not shares_outstanding:
            shares_outstanding = info.get('sharesOutstanding') or 0

        # ── GAAP EPS RECALIBRATION (runs AFTER financials are resolved) ──
        # Now that we have the actual income statement, calculate GAAP EPS
        # and recalibrate P/E if it differs significantly from the info-tag version
        if not fast_mode and financials is not None:
            try:
                if not financials.empty:
                    ni_idx = find_idx(financials, 'Net Income Common Stock Holders')
                    if not ni_idx: ni_idx = find_idx(financials, 'Net Income')
                    
                    if ni_idx and shares_outstanding and shares_outstanding > 0:
                        net_inc = float(financials.loc[ni_idx].iloc[0])
                        # Recalibrate GAAP EPS using fx_rate since financials are now raw (local currency)
                        gaap_eps = (net_inc * fx_rate) / shares_outstanding
                        
                        # Save the Non-GAAP version for display
                        adjusted_eps = trailing_eps
                        
                        # Use GAAP EPS for P/E calculation (actual reported earnings)
                        if gaap_eps and gaap_eps > 0:
                            trailing_eps = gaap_eps
                            pe_ratio = current_price / gaap_eps if current_price else pe_ratio
            except Exception as e_gaap:
                print(f"GAAP recalibration error: {e_gaap}")

        peg_ratio = None
        if pe_ratio and eps_growth and eps_growth > 0:
            peg_ratio = pe_ratio / (eps_growth * 100)
        
        if not peg_ratio:
            peg_ratio = info.get('pegRatio') or info.get('trailingPegRatio')
            
        # Financials for DCF & Margins (Prefer normalized DataFrames over info.get for ADR reliability)
        fcf = None
        try:
            if cashflow is not None and not cashflow.empty:
                fcf_idx = find_idx(cashflow, 'Free Cash Flow')
                if fcf_idx:
                    fcf = float(cashflow.loc[fcf_idx].iloc[0])
                else:
                    ocf_idx = find_idx(cashflow, 'Operating Cash Flow')
                    if ocf_idx:
                        fcf = float(cashflow.loc[ocf_idx].iloc[0])
        except: pass
        
        if fcf is None:
            fcf = info.get('freeCashflow')
            if fcf is None: fcf = info.get('operatingCashflow')
        # shares_outstanding already computed above
        
        # --- TOTAL CASH & DEBT ROBUST FALLBACKS ---
        total_cash = (info.get('totalCash') or 0) * fx_rate
        total_debt = (info.get('totalDebt') or 0) * fx_rate
        
        def get_val_from_dfs(dfs, keys):
            for df in dfs:
                if df is not None and not df.empty:
                    for k in keys:
                        idx = find_idx(df, k)
                        if idx:
                            try:
                                val = float(df.loc[idx].iloc[0])
                                if val != 0: return val
                            except: pass
            return 0

            cash_keys = ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments', 'Total Cash', 'Cash']
            # Try Quarterly BS first (more recent), then Annual
            tc_raw = get_val_from_dfs([q_bs, bs], cash_keys) 
            if tc_raw != 0: total_cash = tc_raw * fx_rate

        if total_debt == 0:
            debt_keys = ['Total Debt', 'Net Debt'] 
            td_raw = get_val_from_dfs([q_bs, bs], debt_keys)
            if td_raw == 0:
                # Try sum of Long Term + Short Term
                def sum_debt(df):
                    if df is None or df.empty: return 0
                    lt_idx = find_idx(df, 'Long Term Debt')
                    st_idx = find_idx(df, 'Current Debt') or find_idx(df, 'Short Long Term Debt')
                    lt = float(df.loc[lt_idx].iloc[0]) if lt_idx else 0
                    st = float(df.loc[st_idx].iloc[0]) if st_idx else 0
                    return lt + st
                
                td_raw = sum_debt(q_bs) or sum_debt(bs)
            
            if td_raw != 0: total_debt = td_raw * fx_rate

        gross_margins = info.get('grossMargins') # Ratio
        profit_margins = info.get('profitMargins') # Ratio
        
        revenue = None
        try:
            if financials is not None and not financials.empty:
                rev_idx = find_idx(financials, 'Total Revenue')
                if rev_idx:
                    revenue = float(financials.loc[rev_idx].iloc[0])
        except: pass
        
        if revenue is None:
            revenue = (info.get('totalRevenue') or 0) * fx_rate
            
        market_cap = info.get('marketCap') # Price * Shares: usually USD for US-listed ADR
        # CALIBRATION: yfinance marketCap can be stale/wrong (e.g. ADBE showing $95B vs real $170B)
        # Always recalculate from price * shares if we have both
        if current_price and shares_outstanding and shares_outstanding > 0:
            calc_cap = current_price * shares_outstanding
            # If yfinance marketCap is off by more than 20%, trust our calculation
            if market_cap is None or abs(calc_cap - market_cap) / calc_cap > 0.20:
                market_cap = calc_cap

        # Scoring Metrics
        debt_to_equity = info.get('debtToEquity')
        
        # Fallback for Financials/Banks or companies with missing info but available totalDebt/bookValue
        if debt_to_equity is None and info.get('totalDebt') and info.get('bookValue') and shares_outstanding:
            equity = info.get('bookValue') * shares_outstanding
            if equity != 0:
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
        roe = info.get('returnOnEquity')
        roa = info.get('returnOnAssets')
        price_to_book = info.get('priceToBook')

        # Dividends
        dividend_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate')
        dividend_yield = info.get('trailingAnnualDividendYield')
        # Fallbacks for extreme yfinance bugs (e.g. GOOGL returning 0.31 instead of 0.0031)
        if dividend_yield is None or dividend_yield > 0.15:
            if dividend_rate and current_price and current_price > 0:
                dividend_yield = dividend_rate / current_price
            else:
                dividend_yield = info.get('dividendYield')
                
        payout_ratio = info.get('payoutRatio')

        # FCF Trend
        fcf_history = []
        historic_fcf_growth = None
        try:
            if cashflow is not None and not cashflow.empty:
                fcf_y = []
                fcf_idx = find_idx(cashflow, 'Free Cash Flow')
                if fcf_idx:
                    fcf_y = cashflow.loc[fcf_idx].dropna().head(5).tolist()
                else:
                    ocf_idx = find_idx(cashflow, 'Operating Cash Flow')
                    if ocf_idx:
                        fcf_y = cashflow.loc[ocf_idx].dropna().head(5).tolist()
                
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
            
        # Historic EPS growth (3Y and 5Y)
        historic_eps_growth_3y = None
        historic_eps_growth_5y = None
        try:
            if financials is not None and not financials.empty:
                eps_idx = find_idx(financials, 'Diluted EPS') or find_idx(financials, 'Basic EPS')
                eps_row = financials.loc[eps_idx] if eps_idx else None
                
                if eps_row is not None:
                    eps_vals = eps_row.dropna().tolist()
                    
                    def calc_yoy_avg(vals, num_years):
                        v = vals[:num_years]
                        if len(v) >= 2:
                            yoy_rates = []
                            for i in range(len(v)-1):
                                new_val, old_val = v[i], v[i+1]
                                if old_val != 0:
                                    g = (new_val - old_val) / abs(old_val)
                                    g = min(max(g, -1.0), 1.0) # Clamp YoY extremes
                                    yoy_rates.append(g)
                            if yoy_rates:
                                avg_g = sum(yoy_rates) / len(yoy_rates)
                                return min(max(avg_g, -0.20), 0.50) # Cap final average
                        return None
                        
                    historic_eps_growth_3y = calc_yoy_avg(eps_vals, 3) # Last 3 years
                    historic_eps_growth_5y = calc_yoy_avg(eps_vals, 5) # Last 5 years
                    historic_eps_growth = historic_eps_growth_5y or historic_eps_growth_3y
        except Exception:
            pass

        # 5Y Average P/E Calibration
        historic_pe_val = None
        if not fast_mode:
            try:
                historic_pe_val = calculate_historic_pe(stock, financials, fx_rate)
            except Exception:
                pass
            
        # Interest coverage & EBIT Margin — reuse already-fetched financials
        interest_coverage = None
        ebit_margin = None
        try:
            if financials is not None and not financials.empty:
                ebit_idx = find_idx(financials, 'EBIT')
                ebit = financials.loc[ebit_idx].dropna() if ebit_idx else None
                
                if ebit is None:
                    ni_idx = find_idx(financials, 'Net Income')
                    ebit = financials.loc[ni_idx].dropna() if ni_idx else None
                    
                if ebit is not None:
                    # Interest Coverage
                    int_idx = find_idx(financials, 'Interest Expense')
                    if int_idx:
                        interest = financials.loc[int_idx].dropna()
                        if interest is not None and not ebit.empty and not interest.empty:
                            ebit_val = ebit.iloc[0]
                            int_val = abs(interest.iloc[0])
                            if int_val > 0:
                                interest_coverage = ebit_val / int_val
                
                # EBIT Margin
                rev_idx = find_idx(financials, 'Total Revenue')
                if rev_idx:
                    rev = financials.loc[rev_idx].dropna()
                    if not ebit.empty and not rev.empty:
                        e_val = ebit.iloc[0]
                        r_val = rev.iloc[0]
                        
                        # Robustness Check for Financials (Visa case):
                        # If e_val is extremely negative or small while 'Operating Income' is better, swap it.
                        op_idx = find_idx(financials, 'Operating Income')
                        if op_idx:
                            op_inc = financials.loc[op_idx].dropna()
                            if not op_inc.empty and op_inc.iloc[0] > e_val:
                                e_val = op_inc.iloc[0]

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

        # Historic Buyback Rate (Robust Multi-Source CALC)
        historic_buyback_rate = 0.0 # Default to 0 instead of None
        try:
            # Method 1: Balance Sheet Share Count Change (PRIMARY - most reliable net calc)
            if bs is not None and not bs.empty:
                shares_idx = find_idx(bs, 'Ordinary Shares Number') or \
                             find_idx(bs, 'Share Issued')
                if shares_idx:
                    shares_hist = bs.loc[shares_idx].dropna()
                    if len(shares_hist) >= 2:
                        vals = shares_hist.head(4).tolist()
                        yoy_rates = []
                        for i in range(len(vals) - 1):
                            s_new = vals[i]      # newer
                            s_old = vals[i + 1]   # older
                            if s_old > 0:
                                # v65: Allow negative results (dilution)
                                reduction = (s_old - s_new) / s_old
                                yoy_rates.append(reduction)
                        if yoy_rates:
                            historic_buyback_rate = sum(yoy_rates) / len(yoy_rates)

            # Method 2: Cash Flow Net Fallback (Only use if Method 1 results in exactly 0.0 or is very small/uncertain)
            # v65: Subtract issuance from repurchases to get the 'Net' cash impact on shares.
            if abs(historic_buyback_rate or 0) < 0.001 and cashflow is not None and not cashflow.empty:
                outflow_idx = find_idx(cashflow, 'Repurchase Of Capital Stock') or find_idx(cashflow, 'Common Stock Payments')
                inflow_idx = find_idx(cashflow, 'Common Stock Issuance')
                
                outflow = 0
                if outflow_idx:
                    outflow = abs(cashflow.loc[outflow_idx].head(3).mean())
                
                inflow = 0
                if inflow_idx:
                    inflow = abs(cashflow.loc[inflow_idx].head(3).mean())
                    
                net_buyback_cash = outflow - inflow
                if market_cap and market_cap > 1000:
                    cf_rate = net_buyback_cash / market_cap
                    # Only use CF if it shows a stronger signal (e.g. clear dilution or clear buyback)
                    if abs(cf_rate) > abs(historic_buyback_rate):
                        historic_buyback_rate = cf_rate
        except Exception:
            pass
        except Exception:
            pass
        operating_cashflow = fcf # Default to FCF if OCF not specifically separated
        try:
            if cashflow is not None and not cashflow.empty:
                if 'Operating Cash Flow' in cashflow.index:
                    operating_cashflow = float(cashflow.loc['Operating Cash Flow'].iloc[0])
        except: pass

        # 1. Dividend Analysis (Streak & CAGR)
        dividend_streak = 0
        dividend_cagr_5y = None
        try:
            if dividends_raw is not None and not dividends_raw.empty:
                # CRITICAL: Check if dividends are RECENT (within last 2 years)
                # yfinance can return ancient dividends (e.g. Adobe 2004-2005)
                import datetime as dt_mod
                latest_div_date = dividends_raw.index[-1]
                if hasattr(latest_div_date, 'year'):
                    years_since_last = dt_mod.datetime.now().year - latest_div_date.year
                else:
                    years_since_last = 99  # Unknown date, treat as ancient
                
                if years_since_last > 3:
                    # Dividends are ancient (more than 3 years old) — company stopped paying
                    dividend_streak = 0
                    dividend_cagr_5y = None
                else:
                    # Group by year
                    div_annual = dividends_raw.groupby(dividends_raw.index.year).sum()
                    
                    # Filter partial years: if latest year < previous year * 0.9, skip it
                    if len(div_annual) >= 2:
                        if div_annual.iloc[-1] < div_annual.iloc[-2] * 0.9:
                            div_annual = div_annual.iloc[:-1]
                    
                    div_years = sorted(div_annual.index.tolist(), reverse=True)
                    
                    # Calculate streak
                    current_streak = 0
                    latest_div_year = div_years[0]
                    this_year = datetime.datetime.now().year
                    
                    if latest_div_year >= this_year - 1:
                        for i in range(len(div_years) - 1):
                            curr_yr = div_years[i]
                            prev_yr = div_years[i+1]
                            if div_annual[curr_yr] >= div_annual[prev_yr] * 0.98: 
                                current_streak += 1
                            else:
                                break
                    dividend_streak = current_streak
                    
                    # 5Y CAGR
                    if len(div_annual) >= 6:
                        latest_val = div_annual.iloc[-1]
                        old_val = div_annual.iloc[-6]
                        if old_val > 0 and latest_val > 0:
                            dividend_cagr_5y = (latest_val / old_val) ** (1/5) - 1
        except Exception as e_div:
            print(f"Error in dividend analysis: {e_div}")

        # 2. Red Flags Generation
        red_flags = []
        try:
            # Payout Risk
            if payout_ratio and payout_ratio > 0.85:
                red_flags.append('⚠️ Dividend Cut Risk: Payout Ratio exceeds 85%.')
            
            # Dilution Risk
            if bs is not None and not bs.empty:
                shares_row = None
                if 'Ordinary Shares Number' in bs.index: shares_row = bs.loc['Ordinary Shares Number']
                elif 'Share Issued' in bs.index: shares_row = bs.loc['Share Issued']
                
                if shares_row is not None:
                    shares_clean = shares_row.dropna()
                    if len(shares_clean) >= 2:
                        latest_shares = shares_clean.iloc[0]
                        prev_shares = shares_clean.iloc[1]
                        if prev_shares > 0:
                            dilution = (latest_shares - prev_shares) / prev_shares
                            if dilution > 0.03:
                                red_flags.append(f'⚠️ Shareholder Dilution: Shares outstanding increased by {(dilution*100):.1f}%.')
        except Exception as e_flags:
            print(f"Error generating red flags: {e_flags}")
        
        if operating_cashflow is None:
            operating_cashflow = info.get('operatingCashflow')
            if operating_cashflow is not None: operating_cashflow *= fx_rate

        # 1. Historical Trends & Base Chart Data (Descending order)
        historical_data = {
            "years": [],
            "revenue": [],
            "eps": [],
            "fcf": [],
            "shares": []
        }
        
        # --- PHASE 0: PRE-CALCULATE NON-GAAP (ADJUSTED) EPS HISTORY ---
        # v87: Hyper-Robust Unified Aggregation (YF + Nasdaq)
        adjusted_history = {}
        try:
            import pandas as _pd
            raw_data_map = {} # {year_str: {date_str: val}}
            
            def add_to_map(dt_obj, eps_val):
                try:
                    # v87: Robust Date offset to map report date to fiscal year
                    adj_dt = dt_obj - datetime.timedelta(days=65)
                    ey = adj_dt.year if adj_dt.month <= fy_end_month else adj_dt.year + 1
                    yr_key = str(ey)
                    dt_key = dt_obj.strftime('%Y-%m-%d')
                    if yr_key not in raw_data_map: raw_data_map[yr_key] = {}
                    # Prioritize newer or non-zero values if collision
                    if dt_key not in raw_data_map[yr_key] or abs(eps_val) > abs(raw_data_map[yr_key][dt_key]):
                        raw_data_map[yr_key][dt_key] = float(eps_val)
                except: pass

            # 1. Source A: Yfinance Earnings Dates
            try:
                ed = stock.get_earnings_dates(limit=32) # Increased limit
                if ed is not None and not ed.empty:
                    c_opts = [c for c in ed.columns if any(x in c for x in ['Reported', 'Actual', 'EPS', 'Earnings'])]
                    col_name = c_opts[0] if c_opts else 'Reported EPS'
                    if col_name in ed.columns:
                        for idx, row in ed.iterrows():
                            val = row.get(col_name)
                            if val is not None and not _pd.isna(val):
                                add_to_map(_pd.to_datetime(idx).tz_localize(None), val)
            except: pass

            # 2. Source B: Nasdaq Surprise API (Often more reliable for Non-GAAP)
            try:
                nq_hist = get_nasdaq_historical_eps(ticker_symbol)
                for entry in nq_hist:
                    add_to_map(entry['date'], entry['eps'])
            except: pass

            # 3. Consolidation with Scaling
            now = datetime.datetime.now()
            curr_y = now.year
            for ey, quarters_dict in raw_data_map.items():
                vals = list(quarters_dict.values())
                if not vals: continue
                
                count = len(vals)
                total = sum(vals)
                ey_int = int(ey)
                
                # Rule: If we have 4 qtrs, it's a full year. 
                # If we have 1-3 qtrs for the current or bridge year, scale it to 4.
                if count >= 4:
                    adjusted_history[ey] = total
                elif count >= 1 and ey_int >= (curr_y - 1):
                    # Robust Scaling for recent/partial years
                    adjusted_history[ey] = (total / count) * 4.0
                else:
                    # Historical years must have at least 3 qtrs to be valid, otherwise use raw sum
                    adjusted_history[ey] = total if count >= 3 else 0

            # Debug Log
            rounded_hist = {k: round(v, 2) for k, v in adjusted_history.items() if v != 0}
            print(f"DEBUG: Consolidated Non-GAAP History for {ticker_symbol}: {rounded_hist}")
            
        except Exception as e:
            print(f"DEBUG: Non-GAAP Aggregation fail: {e}")

        if financials is not None and not financials.empty:
            # We use income stmt as main source of dates (excluding TTM)
            is_cols = [c for c in financials.columns if str(c).upper() != "TTM"]
            for yr_col in sorted(is_cols)[-4:]:
                # Helper for fuzzy extraction within this scope
                def get_metric(df, field, target_date):
                    f_idx = find_idx(df, field)
                    if not f_idx: return 0
                    c_idx = find_nearest_col(df, target_date)
                    if not c_idx: return 0
                    val = df.loc[f_idx, c_idx]
                    return float(val) if not (val is None or (isinstance(val, float) and pd.isna(val))) else 0

                year_label = str(yr_col.year) if hasattr(yr_col, 'year') else str(yr_col)[:4]
                
                r = get_metric(financials, 'Total Revenue', yr_col)
                ni = get_metric(financials, 'Net Income', yr_col)
                
                diluted_eps_idx = find_idx(financials, 'Diluted EPS')
                e = get_metric(financials, diluted_eps_idx, yr_col) if diluted_eps_idx else get_metric(financials, 'Basic EPS', yr_col)
                
                f = get_metric(cashflow, 'Free Cash Flow', yr_col)
                
                s = get_metric(financials, 'Basic Average Shares', yr_col) or \
                    get_metric(financials, 'Diluted Average Shares', yr_col) or \
                    get_metric(bs, 'Ordinary Shares Number', yr_col)
                
                # --- NON-GAAP OVERLAY (v87: Universal Force for Recent History) ---
                if year_label in adjusted_history:
                    adj_val = adjusted_history[year_label]
                    
                    shares_calc = s or next((val for val in historical_data.get("shares", []) if val > 0), None) or \
                                   info.get('shares_outstanding') or info.get('sharesOutstanding') or 2500000000
                    
                    # Scaling shares check
                    if 1000000 < shares_calc < 10000000:
                         shares_calc *= 1000.0
                    
                    implied_ni = adj_val * shares_calc
                    margin_adj = (implied_ni / (r * fx_rate)) if (r and r > 0) else 0
                    margin_gaap = (ni / r) if (r and r > 0) else 0
                    
                    # v87: Extend Force logic to the last 3 fiscal years to ensure data consistency
                    is_recent_history = int(year_label) >= (datetime.datetime.now().year - 3)
                    
                    if is_recent_history and abs(adj_val) > abs(e * 1.02) and adj_val != 0:
                        # Force Adjusted if difference > 2% and it's recent history
                        print(f"DEBUG: FORCING Adjusted {adj_val} over GAAP {e} for {year_label}")
                        e = adj_val
                        if shares_calc > 0: ni = e * shares_calc
                    elif is_recent_history and (not e or e == 0) and abs(adj_val) > 0.01:
                        # Fallback if GAAP is missing
                        e = adj_val
                        if shares_calc > 0: ni = e * shares_calc
                    elif r > 1e9 and e != 0 and abs(margin_gaap) > 0.05 and (margin_adj < (margin_gaap * 0.1) or margin_adj > (margin_gaap * 10)):
                        print(f"DEBUG: REJECTING Adjusted {adj_val} due to extreme margin mismatch")
                    else:
                        # Standard Force if adj_val is non-zero
                        if abs(adj_val) > 0.01:
                            e = adj_val
                            if shares_calc > 0: ni = e * shares_calc
                # REPAIR Logic (v63) Fallback
                elif (not e or e == 0) and ni != 0:
                    s_calc = get_metric(financials, 'Basic Average Shares', yr_col) or \
                             get_metric(financials, 'Diluted Average Shares', yr_col) or \
                             get_metric(bs, 'Ordinary Shares Number', yr_col)
                    if s_calc and s_calc > 0:
                        e = ni / s_calc
                        print(f"DEBUG: Repaired missing EPS for {year_label} using NetIncome/Shares: {e}")
                
                historical_data["years"].append(year_label)
                historical_data["revenue"].append(r * fx_rate)
                historical_data["eps"].append(e * fx_rate)
                historical_data["fcf"].append(f * fx_rate)
                # Shares are unscaled (count)
                historical_data["shares"].append(s)
                
                margin = (ni / r) if (r > 0 and ni is not None) else None
                historical_trends.append({
                    "year": year_label,
                    "revenue": r,
                    "net_margin": margin,
                    "fcf": f
                })
        # 2. Add Projections (Next 2 FYs)
        try:
            if not fast_mode and historical_data["years"] and historical_data["revenue"]:
                # Use Nasdaq Comprehensive Estimates
                nq_estimates = get_nasdaq_comprehensive_estimates(ticker_symbol)
                nq_yearly_eps = nq_estimates.get("yearly_eps", [])
                nq_yearly_rev = nq_estimates.get("yearly_rev", [])
                
                ee_data = future_est.result(timeout=2) if 'future_est' in locals() else None
                rf_data = stock.revenue_estimate
                
                # Calculate avg FCF margin over historical period to project future FCF
                hist_rev = historical_data["revenue"]
                hist_fcf = historical_data["fcf"]
                avg_fcf_margin = 0.10 # default 10%
                valid_margins = [f/r for f, r in zip(hist_fcf, hist_rev) if r > 0]
                if valid_margins:
                    avg_fcf_margin = sum(valid_margins) / len(valid_margins)

                # Use a more robust year detection logic
                last_yr_str = historical_data["years"][-1]
                last_yr = int(last_yr_str) if last_yr_str.isdigit() else datetime.datetime.now().year
                
                # We want the next 2 years (e.g., 2026, 2027 if last was 2025)
                for i in range(1, 3):
                    eps_est = None
                    proj_yr = last_yr + i
                    label = f"{proj_yr} (Est)"
                    # Analysis tab uses Next Year for first estimate generally
                    fy_code = "0y" if i == 1 else "+1y"
                    
                    # 1. Adjusted History Priority (Bridge Year)
                    if str(proj_yr) in adjusted_history:
                        eps_est = adjusted_history[str(proj_yr)]
                    
                    # 2. Nasdaq Priority (v68: Improved Year Alignment)
                    if eps_est is None:
                        # Nasdaq sometimes returns Dec 2026 as the first row even when the bridge year is 2025.
                        # We try to find the matching year in nq_yearly_eps.
                        match = next((row for row in nq_yearly_eps if str(proj_yr) in str(row.get('fiscalEnd') or '')), None)
                        if match:
                            eps_est = safe_nasdaq_float(match.get('consensusEPSForecast'))
                            if eps_est is not None: eps_est *= fx_rate # v69: Fixed scaling
                        elif i <= len(nq_yearly_eps):
                            eps_est = safe_nasdaq_float(nq_yearly_eps[i-1].get('consensusEPSForecast'))
                            if eps_est is not None: eps_est *= fx_rate # v69: Fixed scaling
                    
                    # 3. Yahoo Fallback (Search by Code and then by Year string)
                    if eps_est is None:
                        # Try existing background data first
                        if ee_data is not None and not ee_data.empty:
                            if fy_code in ee_data.index:
                                val = ee_data.loc[fy_code].get('avg')
                                if val is not None and not pd.isna(val): eps_est = float(val) * fx_rate
                            
                            if eps_est is None: # Search for year string in index
                                for idx_name in ee_data.index:
                                    if str(proj_yr) in str(idx_name):
                                        val = ee_data.loc[idx_name].get('avg')
                                        if val is not None and not pd.isna(val):
                                            eps_est = float(val) * fx_rate; break
                            
                            if eps_est is None and (i-1) < len(ee_data):
                                val = ee_data.iloc[i-1].get('avg')
                                if val is not None and not pd.isna(val): eps_est = float(val) * fx_rate
                        
                        # Direct synchronous fallback if still None
                        if eps_est is None:
                            try:
                                e_est_sync = getattr(stock, 'earnings_estimate', None)
                                if e_est_sync is not None and not e_est_sync.empty:
                                    if fy_code in e_est_sync.index:
                                        val = e_est_sync.loc[fy_code].get('avg')
                                        if val is not None and not pd.isna(val): eps_est = float(val) * fx_rate
                                    if eps_est is None:
                                        for idx_name in e_est_sync.index:
                                            if str(proj_yr) in str(idx_name):
                                                val = e_est_sync.loc[idx_name].get('avg')
                                                if val is not None and not pd.isna(val):
                                                    eps_est = float(val) * fx_rate; break
                            except: pass
                    
                    # 4. Last Resort Fallback to historical (only if still None)
                    if eps_est is None:
                        eps_est = historical_data["eps"][-1] if historical_data["eps"] else 0
                    
                    # --- Revenue Estimate ---
                    rev_est = historical_data["revenue"][-1] # fallback
                    
                    # Nasdaq Priority (New)
                    if len(nq_yearly_rev) >= i:
                        raw_val = nq_yearly_rev[i-1].get('consensusRevenueForecast', 0)
                        val = safe_nasdaq_float(raw_val)
                        if val > 0:
                            # Nasdaq revenue scaling check
                            if (historical_data["revenue"][-1] or 0) > 1e6 and val < 10000: val *= 1e9
                            elif (historical_data["revenue"][-1] or 0) > 1e6 and val < 10000000: val *= 1e6
                            # CRITICAL: Nasdaq ADR forecasts are already in USD. Do NOT apply fx_rate.
                            rev_est = val
                    # Fallback to Yahoo
                    elif rf_data is not None and not rf_data.empty:
                        row = None
                        if fy_code in rf_data.index: row = rf_data.loc[fy_code]
                        elif (i-1) < len(rf_data): row = rf_data.iloc[i-1]
                        
                        if row is not None:
                            val = row.get('avg') if hasattr(row, 'get') else row.get('Avg')
                            if val is not None and not pd.isna(val):
                                val = float(val)
                                # SCALE CHECK: Yahoo analysis tab usually reports in Billions (e.g. 26.06)
                                # while financials are absolute (e.g. 26,060,000,000).
                                if rev_est > 1e6 and val < 10000: # Clearly in Billions
                                    val *= 1e9
                                elif rev_est > 1e6 and val < 10000000: # Likely in Millions
                                    val *= 1e6
                                rev_est = val * fx_rate
                    
                    # FCF Estimate (Apply historical margin to rev estimate)
                    fcf_est = rev_est * avg_fcf_margin
                    
                    historical_data["years"].append(label)
                    historical_data["revenue"].append(float(rev_est))
                    historical_data["eps"].append(float(eps_est))
                    historical_data["fcf"].append(float(fcf_est))
                    historical_data["shares"].append(historical_data["shares"][-1])
        except Exception as e_proj:
            print(f"Error adding projections: {e_proj}")
        # 3. Historical Anchors (Last 4 reported fiscal years - Robust Selection)
        historical_anchors = []
        try:
            if financials is not None and not financials.empty:
                # Iterate over already-extracted historical years from step 1
                for i in range(len(historical_data["years"])):
                    # Skip estimate years in anchors table
                    if "Est" in str(historical_data["years"][i]): continue
                    
                    yr_label = historical_data["years"][i]
                    # Find matching datetime col to pull Balance Sheet data
                    is_cols = [c for c in financials.columns if str(c).upper() != "TTM"]
                    yr_col = None
                    for c in is_cols:
                        c_label = str(c.year) if hasattr(c, 'year') else str(c)[:4]
                        if c_label == str(yr_label):
                            yr_col = c; break
                    
                    if not yr_col: continue

                    r_raw = historical_data["revenue"][i]
                    e_raw = historical_data["eps"][i]
                    f_raw = historical_data["fcf"][i]
                    s_raw = historical_data["shares"][i]
                    ni_raw = (r_raw * historical_trends[i]["net_margin"]) if (i < len(historical_trends) and historical_trends[i]["net_margin"]) else 0

                    def get_bs_metric(field, target_date):
                        idx = find_idx(bs, field)
                        if not idx: return 0
                        c_idx = find_nearest_col(bs, target_date)
                        if not c_idx: return 0
                        val = bs.loc[idx, c_idx]
                        return float(val) if not pd.isna(val) else 0

                    c_raw = get_bs_metric('Cash And Cash Equivalents', yr_col)
                    
                    # --- ROBUST DEBT DETECTION (v71) ---
                    # User confirmed $83B is the correct Total Debt from their Balance Sheet view.
                    # We will use the raw metric but keep components as fallbacks.
                    d_raw = get_bs_metric('Total Debt', yr_col)
                    lt_debt = get_bs_metric('Long Term Debt', yr_col) or get_bs_metric('Total Long Term Debt', yr_col)
                    st_debt = get_bs_metric('Short Long Term Debt', yr_col) or get_bs_metric('Current Debt', yr_col) or get_bs_metric('Commercial Paper', yr_col)
                    
                    if d_raw == 0:
                        d_raw = lt_debt + st_debt

                    assets = get_bs_metric('Total Assets', yr_col)
                    liabs = get_bs_metric('Current Liabilities', yr_col)

                    # Calculations
                    margin_v = (historical_trends[i]["net_margin"] * 100.0) if (i < len(historical_trends) and historical_trends[i]["net_margin"]) else None
                    
                    # --- PARTIAL YEAR SANITY CHECK ---
                    # If margin in latest year drops > 60% vs previous year with similar revenue, it's likely a partial year.
                    if i > 0 and margin_v and i == (len(historical_data["years"]) - 1):
                        prev_m = (historical_trends[i-1]["net_margin"] * 100.0)
                        if prev_m > 5 and margin_v < (prev_m * 0.4):
                             # Look at Revenue. If Revenue is also low, it's definitely partial.
                             # If Revenue is high but margin low, it might be an unscaled Income Statement.
                             yr_label = f"{yr_label} (Partial)"
                             print(f"DEBUG: Tagging {yr_label} as Partial due to margin drop ({margin_v:.1f}% vs {prev_m:.1f}%)")

                    cr_v = (c_raw / liabs) if liabs > 0 else (get_bs_metric('Total Current Assets', yr_col) / liabs if liabs > 0 else None)
                    roic_v = (ni_raw / (assets - liabs) * 100.0) if (assets - liabs) > 0 else None
                    
                    historical_anchors.append({
                        "year": yr_label,
                        "revenue_b": round((r_raw * fx_rate) / 1e9, 2),
                        "eps": round(e_raw * fx_rate, 2),
                        "fcf_b": round((f_raw * fx_rate) / 1e9, 2),
                        "net_margin_pct": f"{margin_v:.1f}%" if margin_v is not None else "0.0%",
                        "cash_b": round(c_raw / 1e9, 2),
                        "total_debt_b": round(d_raw / 1e9, 2),
                        "shares_out_b": round(s_raw / 1e9, 2),
                        "roic_pct": f"{roic_v:.1f}%" if roic_v is not None else "0.0%",
                        "current_ratio": round(cr_v, 2) if cr_v is not None else None
                    })
            # Reverse anchors so newest is first for the UI table
            historical_anchors.reverse()
            
            # --- PHASE 2: DATA INTEGRITY REFINEMENT (SMCI FIX) ---
            # 1. Update ROIC from processed anchors (avoid stale info tags)
            if historical_anchors:
                latest = historical_anchors[0]
                # Extract numeric value from "9.0%" or use 0
                try:
                    val_str = latest.get("roic_pct", "0").replace("%", "")
                    roic = float(val_str) / 100.0
                except: pass
                
            # 2. Update Revenue Growth from annual anchors if quarterly is misleading (SMCI FIX)
            if len(historical_anchors) >= 2:
                latest_rev = historical_anchors[0]["revenue_b"]
                prev_rev = historical_anchors[1]["revenue_b"]
                if prev_rev > 0:
                    annual_growth = (latest_rev - prev_rev) / prev_rev
                    # v42: Critical check for massive growth (123% vs 1.23%)
                    # yfinance info['revenueGrowth'] for SMCI is 1.234 (123.4%)
                    # Some code might divide this by 100 incorrectly. We ensure it's kept as a proper percentage.
                    if annual_growth > 0.15 and (revenue_growth_val or 0) < 0.10:
                        print(f"DEBUG: SMCI Fix - Replacing stale/mis-normalized growth {revenue_growth_val} with {annual_growth}")
                        revenue_growth_val = annual_growth
                    elif (revenue_growth_val or 0) > 1.0 and (revenue_growth_val or 0) < 2.0 and annual_growth > 1.0:
                         # It's already in the correct format (1.23 = 123%)
                         pass

            # 3. Synchronize Latest Anchor Shares with Live Sidebar (SMCI FIX)
            # The sidebar uses info.get('sharesOutstanding') while the chart used BS.
            # We force them to align for the newest data year.
            if historical_anchors and shares_outstanding:
                live_shares_b = shares_outstanding / 1e9
                latest_anchor = historical_anchors[0]
                if abs(latest_anchor.get("shares_out_b", 0) - live_shares_b) > 0.01:
                    print(f"DEBUG: Synchronizing latest anchor shares ({latest_anchor.get('shares_out_b')}) to live value ({live_shares_b})")
                    latest_anchor["shares_out_b"] = round(live_shares_b, 3)
                    if len(historical_data["shares"]) > 0:
                        historical_data["shares"][0] = shares_outstanding

            # --- SYSTEMIC RATIO AUDIT (Calculated > Reported) ---
            net_margin_calc = None
            if bs is not None and not bs.empty and financials is not None and not financials.empty:
                try:
                    # Use most recent column (excluding TTM)
                    target_date = [c for c in financials.columns if str(c).upper() != "TTM"]
                    if target_date:
                        target_date = sorted(target_date)[-1]
                        
                        def get_f_metric(df, keys, date):
                            for k in keys:
                                idx = find_idx(df, k)
                                if idx:
                                    c_idx = find_nearest_col(df, date)
                                    if c_idx:
                                        val = df.loc[idx, c_idx]
                                        if not pd.isna(val): return float(val)
                            return 0

                        # 1. Margins
                        rev_val = get_f_metric(financials, ['Total Revenue', 'Revenue'], target_date)
                        ni_val = get_f_metric(financials, ['Net Income Common Stock Holders', 'Net Income'], target_date)
                        op_inc_val = get_f_metric(financials, ['Operating Income', 'EBIT'], target_date)
                        
                        if rev_val > 0:
                            ebit_margin = op_inc_val / rev_val
                            net_margin_calc = ni_val / rev_val
                        
                        # 2. Balance Sheet Ratios
                        ca = get_f_metric(bs, ['Current Assets', 'Total Current Assets'], target_date)
                        cl = get_f_metric(bs, ['Current Liabilities', 'Total Current Liabilities'], target_date)
                        equity = get_f_metric(bs, ['Common Stock Equity', 'Stockholders Equity', 'Total Equity'], target_date)
                        assets_val = get_f_metric(bs, ['Total Assets'], target_date)
                        debt_val = get_f_metric(bs, ['Total Debt'], target_date)
                        
                        if cl > 0: current_ratio = ca / cl
                        if equity > 0:
                            debt_to_equity = debt_val / equity
                            roe = ni_val / equity
                        if assets_val > 0:
                            roa = ni_val / assets_val
                        
                        # 3. Market Cap Calibration (Absolute Sync v42)
                        if current_price and shares_outstanding:
                            # Re-calibrate market cap and all dependent ratios
                            market_cap = float(current_price * shares_outstanding)
                            if rev_val and rev_val > 0:
                                 ps_ratio = market_cap / rev_val
                            if ni_val and ni_val > 0:
                                 pe_ratio = market_cap / ni_val
                            print(f"DEBUG: Hyper-Sync Market Cap: {market_cap/1e9:.2f}B using {shares_outstanding/1e6:.1f}M shares")
                            
                except Exception as e_audit:
                    print(f"Ratio Audit Error for {ticker_symbol}: {e_audit}")

        except Exception as e_anch:
            print(f"Error adding anchors: {e_anch}")

        # 3. Next Earnings Extraction
        next_earnings_date = "N/A"
        try:
            # Try calendar first
            cal = stock.calendar
            if cal is not None:
                # Handle both DataFrame and Dict return types from yfinance
                ed = None
                if isinstance(cal, dict):
                    ed = cal.get('Earnings Date')
                elif hasattr(cal, 'empty') and not cal.empty:
                    ed = cal.get('Earnings Date')
                
                if ed is not None:
                    if isinstance(ed, list) and len(ed) > 0:
                        next_earnings_date = ed[0].strftime('%Y-%m-%d')
                    else:
                        next_earnings_date = str(ed)
            
            if next_earnings_date == "N/A":
                # Try timestamp fallback
                ts = info.get('earningsTimestamp') or info.get('nextEarningsDate')
                if ts:
                    next_earnings_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        except Exception as e_earn:
            print(f"Error fetching earnings: {e_earn}")

        # Final return object (Diagnostic-Rich v22)
        return {
            "ticker": ticker_symbol.upper(),
            "name": name,
            "historical_anchors": historical_anchors,
            "current_price": current_price,
            "data_source": data_source,
            "sector": sector,
            "industry": industry,
            "trailing_eps": trailing_eps,
            "adjusted_eps": adjusted_eps,
            "peg_ratio": peg_ratio,
            "pe_ratio": pe_ratio,
            "forward_pe": forward_pe,
            "ps_ratio": ps_ratio,
            "fwd_ps": fwd_ps,
            "eps_growth": eps_growth,
            "fcf": fcf,
            "fcf_history": fcf_history,
            "operating_cashflow": operating_cashflow,
            "market_cap": market_cap,
            "shares_outstanding": shares_outstanding,
            "total_cash": total_cash,
            "total_debt": total_debt,
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "roic": roic,
            "roe": roe,
            "roa": roa,
            "interest_coverage": interest_coverage,
            "price_to_book": price_to_book,
            "revenue": revenue,
            "revenue_growth": revenue_growth_val,
            "earnings_growth": earnings_growth_val,
            "next_3y_rev_est": next_3y_rev_est,
            "ebitda": info.get('ebitda') or (float(financials.loc[find_idx(financials, 'EBITDA')].iloc[0]) if financials is not None and find_idx(financials, 'EBITDA') else None),
            "operating_margin": ebit_margin or info.get('operatingMargins'),
            "ebit_margin": ebit_margin,
            "net_margin": net_margin_calc or info.get('profitMargins'),
            "dividend_yield": dividend_yield,
            "dividend_rate": dividend_rate,
            "dividend_streak": dividend_streak,
            "dividend_cagr_5y": dividend_cagr_5y,
            "payout_ratio": payout_ratio,
            "insider_ownership": info.get('heldPercentInsiders'),
            "eps_growth": normalize_growth(eps_growth),
            "eps_growth_period": eps_growth_period,
            "eps_growth_3y": normalize_growth(historic_eps_growth_3y),
            "eps_growth_5y": normalize_growth(historic_eps_growth_5y),
            "eps_growth_5y_consensus": normalize_growth(eps_growth_5y_consensus),
            "eps_growth_nasdaq_3y": normalize_growth(nasdaq_growth_3y),
            "historic_eps_growth": normalize_growth(historic_eps_growth),
            "historic_fcf_growth": normalize_growth(historic_fcf_growth),
            "historic_bvps_growth": normalize_growth(next((calc_yoy_avg(bs.loc[idx].dropna().tolist(), 3) for idx in ['Common Stock Equity', 'Total Assets'] if bs is not None and not bs.empty and idx in bs.index), None)),
            "historic_buyback_rate": normalize_growth(historic_buyback_rate),
            "pe_historic": historic_pe_val or info.get('trailingPE'),
            "historical_data": historical_data,
            "historical_trends": historical_trends,
            "business_summary": info.get('longBusinessSummary', 'N/A')[:200] + "...",
            "next_earnings_date": next_earnings_date,
            "netInterestMargin": info.get('netInterestMargin') or (float(financials.loc[find_idx(financials, 'Net Interest Income')].iloc[0]) / (float(bs.loc[find_idx(bs, 'Total Assets')].iloc[0]) if bs is not None and find_idx(bs, 'Total Assets') else (info.get('totalAssets') or 1)) if financials is not None and find_idx(financials, 'Net Interest Income') else None),
            "cet1_ratio": info.get('commonEquityTier1Ratio') or (float(bs.loc[find_idx(bs, 'Common Equity Tier 1')].iloc[0]) if bs is not None and find_idx(bs, 'Common Equity Tier 1') else (float(bs.loc[find_idx(bs, 'Total Equity')].iloc[0]) / float(bs.loc[find_idx(bs, 'Total Assets')].iloc[0]) if bs is not None and find_idx(bs, 'Total Assets') and find_idx(bs, 'Total Equity') and float(bs.loc[find_idx(bs, 'Total Assets')].iloc[0]) > 0 else None)),
            "red_flags": red_flags,
            "company_overview_synthesis": get_company_synthesis(ticker_symbol, info)
        }
    except Exception as e:
        print(f"Error in get_analyst_data for {ticker_symbol}: {e}")
        return {"error": str(e)}

# --- TICKER SEARCH ENGINE (v59) ---
MASTER_TICKERS = [
    {"ticker": "AAPL", "name": "Apple Inc."}, {"ticker": "MSFT", "name": "Microsoft Corp."},
    {"ticker": "GOOGL", "name": "Alphabet Inc. (Class A)"}, {"ticker": "AMZN", "name": "Amazon.com Inc."},
    {"ticker": "NVDA", "name": "NVIDIA Corporation"}, {"ticker": "META", "name": "Meta Platforms Inc."},
    {"ticker": "TSLA", "name": "Tesla Inc."}, {"ticker": "BRK-B", "name": "Berkshire Hathaway Inc."},
    {"ticker": "UNH", "name": "UnitedHealth Group Inc."}, {"ticker": "V", "name": "Visa Inc."},
    {"ticker": "JPM", "name": "JPMorgan Chase & Co."}, {"ticker": "LLY", "name": "Eli Lilly and Co."},
    {"ticker": "XOM", "name": "Exxon Mobil Corp."}, {"ticker": "AVGO", "name": "Broadcom Inc."},
    {"ticker": "MA", "name": "Mastercard Inc."}, {"ticker": "WMT", "name": "Walmart Inc."},
    {"ticker": "PG", "name": "Procter & Gamble Co."}, {"ticker": "JNJ", "name": "Johnson & Johnson"},
    {"ticker": "HD", "name": "Home Depot Inc."}, {"ticker": "COST", "name": "Costco Wholesale Corp."},
    {"ticker": "ADBE", "name": "Adobe Inc."}, {"ticker": "ORCL", "name": "Oracle Corp."},
    {"ticker": "AMD", "name": "Advanced Micro Devices"}, {"ticker": "CRM", "name": "Salesforce Inc."},
    {"ticker": "NFLX", "name": "Netflix Inc."}, {"ticker": "BAC", "name": "Bank of America Corp."},
    {"ticker": "PEP", "name": "PepsiCo Inc."}, {"ticker": "KO", "name": "Coca-Cola Co."},
    {"ticker": "CVX", "name": "Chevron Corp."}, {"ticker": "ACN", "name": "Accenture plc"},
    {"ticker": "TMO", "name": "Thermo Fisher Scientific"}, {"ticker": "ABT", "name": "Abbott Laboratories"},
    {"ticker": "MRK", "name": "Merck & Co. Inc."}, {"ticker": "DIS", "name": "Walt Disney Co."},
    {"ticker": "CSCO", "name": "Cisco Systems Inc."}, {"ticker": "DHR", "name": "Danaher Corp."},
    {"ticker": "WFC", "name": "Wells Fargo & Co."}, {"ticker": "INTC", "name": "Intel Corp."},
    {"ticker": "INTU", "name": "Intuit Inc."}, {"ticker": "IBM", "name": "IBM Corp."},
    {"ticker": "QCOM", "name": "Qualcomm Inc."}, {"ticker": "CAT", "name": "Caterpillar Inc."},
    {"ticker": "AMAT", "name": "Applied Materials Inc."}, {"ticker": "GE", "name": "General Electric Co."},
    {"ticker": "TXN", "name": "Texas Instruments Inc."}, {"ticker": "PLTR", "name": "Palantir Technologies"},
    {"ticker": "SMCI", "name": "Super Micro Computer Inc."}, {"ticker": "UBER", "name": "Uber Technologies"},
    {"ticker": "NKE", "name": "NIKE Inc."}, {"ticker": "SBUX", "name": "Starbucks Corp."}
]

def ticker_search(q: str):
    if not q: return []
    q = q.upper().strip()
    
    hits = []
    # 1. Exact ticker matches
    for item in MASTER_TICKERS:
        if item["ticker"] == q:
            hits.append(item)
    
    # 2. Ticker starts with
    for item in MASTER_TICKERS:
        if item["ticker"].startswith(q) and item not in hits:
            hits.append(item)
            
    # 3. Name matches
    for item in MASTER_TICKERS:
        if q in item["name"].upper() and item not in hits:
            hits.append(item)
            
    return hits[:8]

# --- V41: Persistent Sector Cache ---
def get_competitors_data(target_ticker, sector=None, industry=None, limit=3, include_growth=True) -> list:
    """ Fetches metrics for peer companies. v41: Autonomously resolves sector if missing. """
    try:
        target_ticker = target_ticker.upper()
        target_industry = industry or ""
        
        # 1. AUTONOMOUS RESOLUTION (v41): If sector is missing (Parallel Blitz), check KV or yf
        if not sector:
            kv_sec_key = f"sec_v1_{target_ticker}"
            cached_meta = kv_get(kv_sec_key)
            if cached_meta:
                sector = cached_meta.get("sector")
                target_industry = cached_meta.get("industry")
            else:
                # Fast info fetch
                main_yf = yf.Ticker(target_ticker)
                inf = main_yf.info
                sector = inf.get("sector")
                target_industry = inf.get("industry")
                if sector:
                    kv_set(kv_sec_key, {"sector": sector, "industry": target_industry}, ex=604800) # 1 week

        # HARDCODED INDUSTRY FALLBACKS (v63: Ensure quality for high-profile tickers if info fails)
        if not target_industry:
            if target_ticker == "FDS": target_industry = "Financial Data & Stock Exchanges"
            if target_ticker == "MSCI": target_industry = "Financial Data & Stock Exchanges"
            if target_ticker == "NDAQ": target_industry = "Financial Data & Stock Exchanges"
            if target_ticker == "ADBE": target_industry = "Software - Infrastructure"
            if target_ticker == "SMCI": target_industry = "Computer Hardware"

        # 2. SEED/PEER DISCOVERY
        peers = []
        FINNHUB_KEY = os.environ.get('FINNHUB_API_KEY')

        if FINNHUB_KEY:
            # 1. Try Finnhub
            try:
                url = f"https://finnhub.io/api/v1/stock/peers?symbol={target_ticker}&token={FINNHUB_KEY}"
                resp = requests.get(url, timeout=3)
                if resp.status_code == 200:
                    peers = resp.json()
            except Exception as e:
                print(f"Finnhub API call error: {e}")

        # 1.5 Filter and Check for Dynamic Fallback
        if peers:
            # Filter out tickers with dots (international/local exchange symbols)
            peers = [p for p in peers if '.' not in p]
            
        if not peers or len(peers) < 2:
            print(f"Few or no US peers for {target_ticker}, attempting Yahoo Recommendation fallback...")
            try:
                # Yahoo Recommendations API
                url = f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/{target_ticker}"
                headers = {'User-Agent': get_random_agent()}
                resp = requests.get(url, headers=headers, timeout=3)
                if resp.status_code == 200:
                    rec_json = resp.json()
                    results = rec_json.get('finance', {}).get('result', [])
                    if results:
                        rec_symbols = results[0].get('recommendedSymbols', [])
                        rec_peers = [r.get('symbol') for r in rec_symbols if r.get('symbol')]
                        # Filter out tickers with dots (international/local exchange symbols)
                        rec_peers = [p for p in rec_peers if '.' not in p]
                        if rec_peers:
                            peers = rec_peers
            except Exception as e_rec:
                print(f"Yahoo Recommendation fallback error: {e_rec}")

        # 2. Universal Scraper Fallback (DELETED FOR SPEED)
        # Using HTTP requests and parsing huge HTML dumps via RegEx was crippling the backend speed.
        
        # 2.5 INDUSTRY QUALITY SHIELD (v63): Force high-quality peers and prune irrelevant symbols (like COIN for FDS)
        if target_industry and ("Financial Data" in target_industry or "Exchange" in target_industry):
            hq_peers = ["MSCI", "NDAQ", "ICE", "SPGI", "MCO", "CBOE"]
            peers = list(dict.fromkeys(peers + hq_peers))
            irrelevant = ["COIN"] # Yahoo often incorrectly suggests COIN for data providers
            peers = [p for p in peers if p.upper() not in irrelevant]

        if not peers:
            if sector == "Technology":
                # Industry specific fallbacks
                if "Semiconductor" in target_industry or target_ticker in ["CRDO", "ALAB", "MRVL"]:
                    # Ensure high-confidence chip peers
                    peers = ["ALAB", "MRVL", "AVGO", "NVDA", "AMD", "ARM", "MU", "CRDO"]
                elif "Software" in target_industry or target_ticker == "ADBE":
                    peers = ["MSFT", "ADBE", "CRM", "ORCL", "SNOW", "PLTR", "DDOG", "CRWD"]
                elif "Hardware" in target_industry or target_ticker == "SMCI":
                    peers = ["DELL", "HPE", "NTAP", "STX", "WDC", "AAPL", "SMCI"]
                else:
                    peers = ["IBM", "IT", "CTSH", "INFY", "ACN", "MSFT", "AAPL", "GOOGL"]
            elif sector == "Financial Services":
                if "Bank" in target_industry or "Credit" in target_industry:
                    peers = ["JPM", "BAC", "WFC", "C", "GS", "MS", "AXP"]
                elif "Data" in target_industry or "Exchange" in target_industry:
                    peers = ["MSCI", "NDAQ", "ICE", "SPGI", "MCO", "CBOE", "FDS"]
                else:
                    peers = ["SCHW", "MSI", "GS", "JPM", "BAC", "IBKR", "WFC"]
            elif sector == "Consumer Cyclical":
                if "Autos" in target_industry:
                    peers = ["TSLA", "TM", "GM", "F", "FSR", "RIVN"]
                else:
                    peers = ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX"]
            elif sector == "Consumer Defensive":
                if "Retail" in target_industry or "Discount" in target_industry:
                    peers = ["WMT", "COST", "TGT", "DG", "DLTR", "BJ"]
                elif "Beverages" in target_industry:
                    peers = ["KO", "PEP", "MNST", "KDP", "CELH"]
                else:
                    peers = ["PG", "KO", "PEP", "COST", "WMT", "PM"]
            elif sector == "Real Estate":
                peers = ["PLD", "AMT", "EQIX", "CCI", "PSA", "O", "VICI"]
            elif sector == "Energy":
                peers = ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX"]
            elif sector == "Healthcare":
                if "Drug" in target_industry or "Biotech" in target_industry:
                    peers = ["LLY", "JNJ", "ABBV", "MRK", "PFE", "AMGN"]
                else:
                    peers = ["UNH", "TMO", "ISRG", "DHR", "LLY", "VRTX"]
            elif sector == "Basic Materials":
                peers = ["FCX", "LIN", "APD", "NEM", "CTVA", "SHW", "ECL"]
            else:
                # Absolute last resort across any US stock
                peers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]
        # 3. BATCH EXTRACTION (Primary: yfinance)
        candidates = [p.upper() for p in peers if p.upper() != target_ticker.upper() and '.' not in p][:3]
        final_peers = []

        # --- Attempt yfinance with manual session (to handle crumbs better) ---
        try:
            print(f"DEBUG: Attempting yfinance batch for {candidates}")
            batch = yf.Tickers(" ".join(candidates))
            def fetch_peer_info(t):
                try:
                    now = time.time()
                    # Layer 1: Memory
                    if t in _peer_info_cache:
                        cached_inf, ts = _peer_info_cache[t]
                        if now - ts < 86400: return cached_inf
                    
                    # Layer 2: Persistent KV Store (Upstash/Redis)
                    kv_key = f"peer_v1_{t.upper()}"
                    kv_data = kv_get(kv_key)
                    if kv_data and isinstance(kv_data, dict):
                        _peer_info_cache[t] = (kv_data, now)
                        return kv_data

                    # Layer 3: Network
                    inf = batch.tickers[t].info
                    if inf and (inf.get('regularMarketPrice') or inf.get('currentPrice')):
                        p_data = {
                            "ticker": t,
                            "name": inf.get('shortName') or inf.get('longName') or t,
                            "price": inf.get('regularMarketPrice') or inf.get('currentPrice'),
                            "pe_ratio": inf.get('trailingPE') or inf.get('forwardPE'),
                            "market_cap": inf.get('marketCap'),
                            "ps_ratio": inf.get('priceToSalesTrailing12Months') or inf.get('priceToSales'),
                            "eps": inf.get('trailingEps') or inf.get('forwardEps'),
                            "operating_margin": inf.get('operatingMargins') or inf.get('ebitdaMargins'),
                            "industry": inf.get('industry') or target_industry,
                            "sector": inf.get('sector') or sector
                        }
                        if include_growth:
                            p_data["revenue_growth"] = inf.get('revenueGrowth') or inf.get('revenueQuarterlyGrowth')
                            p_data["earnings_growth"] = inf.get('earningsGrowth') or inf.get('earningsQuarterlyGrowth')
                            if p_data["earnings_growth"] is None and inf.get('trailingEps') and inf.get('forwardEps'):
                                te, fe = inf['trailingEps'], inf['forwardEps']
                                if te > 0: p_data["earnings_growth"] = (fe - te) / te
                        
                        # Update both caches
                        _peer_info_cache[t] = (p_data, now)
                        kv_set(kv_key, p_data, ex=86400) # 24h TTL
                        return p_data
                except Exception as e:
                    print(f"DEBUG: fetch_peer_info error for {t}: {e}")
                    return None
                return None

            ex = concurrent.futures.ThreadPoolExecutor(max_workers=3)
            futs = {ex.submit(fetch_peer_info, t): t for t in candidates}
            try:
                for f in concurrent.futures.as_completed(futs, timeout=5):
                    t = futs[f]
                    try:
                        res = f.result(timeout=1)
                        if res: final_peers.append(res)
                    except Exception as e:
                        print(f"DEBUG: Peer {t} failed: {e}")
            except concurrent.futures.TimeoutError:
                print("DEBUG: Peer fetch batch timed out")
            finally:
                ex.shutdown(wait=False)
        except Exception as e:
            print(f"DEBUG: yfinance batch failed: {e}")

        # --- Fallback 1: Finnhub (Detailed Metrics) ---
        fh_key = os.environ.get('FINNHUB_API_KEY')
        if len(final_peers) < 2 and fh_key:
            print("DEBUG: Yahoo failed, trying Finnhub...")
            for t in candidates:
                if any(p['ticker'] == t for p in final_peers): continue
                try:
                    q = requests.get(f"https://finnhub.io/api/v1/quote?symbol={t}&token={fh_key}", timeout=5).json()
                    m = requests.get(f"https://finnhub.io/api/v1/stock/metric?symbol={t}&metric=all&token={fh_key}", timeout=5).json().get('metric', {})
                    if q.get('c'):
                        final_peers.append({
                            "ticker": t, "name": t, "price": q['c'], "pe_ratio": m.get('peExclExtraTTM'),
                            "market_cap": (m.get('marketCapitalization',0)*1e6) if m.get('marketCapitalization') else None,
                            "operating_margin": (m.get('operatingMarginTTM', 0)/100.0) if m.get('operatingMarginTTM') else None,
                            "revenue_growth": (m.get('revenueGrowthTTM', 0)/100.0) if m.get('revenueGrowthTTM') else None,
                            "earnings_growth": (m.get('epsGrowthTTM', 0)/100.0) if m.get('epsGrowthTTM') else None,
                            "industry": target_industry, "sector": sector
                        })
                except: continue

        # --- Fallback 2: Direct Chart API (Prices ONLY - Last Resort for visuals) ---
        if len(final_peers) < limit:
            print("DEBUG: Trying Direct Chart fallback for prices...")
            for t in candidates:
                if any(p['ticker'] == t for p in final_peers): continue
                try:
                    c_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=1d&range=1d"
                    c_resp = requests.get(c_url, headers={'User-Agent': get_random_agent()}, timeout=5).json()
                    meta = c_resp.get('chart', {}).get('result', [{}])[0].get('meta', {})
                    if meta.get('regularMarketPrice'):
                        final_peers.append({
                            "ticker": t, "name": t, "price": meta['regularMarketPrice'],
                            "pe_ratio": None, "industry": target_industry, "sector": sector
                        })
                except: continue

        # Final Deduplication
        unique = []
        seen_t = {target_ticker.upper()}
        for p in final_peers:
            if p['ticker'] not in seen_t:
                unique.append(p)
                seen_t.add(p['ticker'])
        
        return unique[:limit]
        
    except Exception as e:
        print(f"Global competitors failure for {target_ticker}: {e}")
        return []

def get_lightweight_company_data(ticker_symbol: str):
    """Fetches a minimal set of data for competitor comparison using yfinance and Finnhub fallbacks."""
    ticker_symbol = ticker_symbol.upper()
    
    # Check KV Cache (Forced Bust v13 for Growth)
    cache_key = f"peer_v13_{ticker_symbol}"
    cached = kv_get(cache_key)
    if cached:
        return cached

    data = None
    try:
        # Use yfinance as it handles Crumbs and Cookies automatically
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        if info and info.get('currentPrice'):
            fx_rate = get_fx_rate(info)
            data = {
                "ticker": ticker_symbol,
                "name": info.get('shortName') or info.get('longName') or ticker_symbol,
                "price": info.get('currentPrice') or info.get('regularMarketPrice'),
                "pe_ratio": info.get('trailingPE') or info.get('forwardPE'),
                "peg_ratio": info.get('pegRatio'),
                "eps": info.get('trailingEps'),
                "market_cap": info.get('marketCap'),
                "ps_ratio": info.get('priceToSalesTrailing12Months') or info.get('priceToSales'),
            }
            # Scale currencies if not USD
            if fx_rate != 1.0:
                for k in ["price", "eps", "market_cap"]:
                    if data.get(k): data[k] *= fx_rate

    except Exception as e:
        print(f"yfinance peer fetch failed for {ticker_symbol}: {e}")

    # Final Nuclear Fallback: Finnhub
    if not data or not data.get('pe_ratio') or not data.get('revenue_growth'):
        try:
            fh_key = os.environ.get('FINNHUB_API_KEY')
            if fh_key:
                m_url = f"https://finnhub.io/api/v1/stock/metric?symbol={ticker_symbol}&metric=all&token={fh_key}"
                q_url = f"https://finnhub.io/api/v1/quote?symbol={ticker_symbol}&token={fh_key}"
                m_resp = requests.get(m_url, timeout=5); q_resp = requests.get(q_url, timeout=5)
                if m_resp.status_code == 200 and q_resp.status_code == 200:
                    m = m_resp.json().get('metric', {}); q = q_resp.json()
                    data = data or {"ticker": ticker_symbol, "name": ticker_symbol}
                    data["price"] = data.get('price') or q.get('c')
                    data["pe_ratio"] = data.get('pe_ratio') or m.get('peExclExtraTTM')
                    data["market_cap"] = data.get('market_cap') or (m.get('marketCapitalization', 0) * 1000000)
                    data["eps"] = data.get('eps') or m.get('epsExclExtraItemsTTM')
                    data["operating_margin"] = data.get('operating_margin') or (m.get('operatingMarginTTM', 0)/100.0 if m.get('operatingMarginTTM') else None)
                    data["revenue_growth"] = data.get('revenue_growth') or (m.get('revenueGrowthTTM', 0)/100.0 if m.get('revenueGrowthTTM') else None)
                    data["earnings_growth"] = data.get('earnings_growth') or (m.get('epsGrowthTTM', 0)/100.0 if m.get('epsGrowthTTM') else None)
        except:
            pass

    if data and data.get('price'):
        kv_set(cache_key, data, ex=86400)
        return data
    
    return None

def get_nasdaq_comprehensive_estimates(ticker):
    """Fetches high-quality analyst projections from Nasdaq or fallbacks."""
    try:
        url = f"https://api.nasdaq.com/api/analyst/{ticker}/estimates"
        headers = {"User-Agent": get_random_agent(), "Accept": "application/json"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            d = resp.json().get('data', {})
            return {
                "yearly_eps": d.get('yearlyEpsForecast', []),
                "yearly_rev": d.get('yearlyRevenueForecast', [])
            }
    except Exception as e:
        print(f"Nasdaq Estimate Fetch Failed for {ticker}: {e}")
    return {"yearly_eps": [], "yearly_rev": []}


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
        return {"trailing_pe": 20.0, "forward_pe": 18.0}

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
        fx_rate = get_fx_rate(info)
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

        # ── EPS & Revenue Estimates ─────────────────────────────────────────
        # Priority 1: Yahoo Finance (Usually contains Non-GAAP consensus)
        try:
            e_est = stock.earnings_estimate
            if e_est is not None and not e_est.empty:
                for idx, row in e_est.iterrows():
                    lbl = str(idx)
                    label = labels.get(lbl, lbl)
                    eps_estimates.append({
                        "period": label,
                        "avg": round(float(row.get('avg', 0)), 2),
                        "growth": float(row.get('growth', 0)) if row.get('growth') else None,
                        "status": "estimate"
                    })
            
            r_est = stock.revenue_estimate
            if r_est is not None and not r_est.empty:
                for idx, row in r_est.iterrows():
                    lbl = str(idx)
                    label = labels.get(lbl, lbl)
                    rev_estimates.append({
                        "period": label,
                        "avg": round(float(row.get('avg', 0)), 2),
                        "growth": float(row.get('growth', 0)) if row.get('growth') else None,
                        "status": "estimate"
                    })
        except Exception as e:
            print(f"[Analyst] Yahoo Estimates fail: {e}")

        # Priority 2: Nasdaq Fallback/Supplement (if lists still empty)
        if not eps_estimates:
            try:
                nq_est = get_nasdaq_comprehensive_estimates(ticker_symbol)
                nq_yearly_eps = nq_est.get("yearly_eps", [])
                
                for i, y_row in enumerate(nq_yearly_eps[:3]):
                     date_val = y_row.get('fiscalYearEnd') or y_row.get('fiscalEnd')
                     label = f"FY {date_val}" if date_val else "N/A"
                     avg_val = safe_nasdaq_float(y_row.get('consensusEPSForecast'))
                     if avg_val is not None:
                         eps_estimates.append({
                             "period": label,
                             "period_code": f"+{i}y",
                             "avg": round(avg_val, 2),
                             "status": "estimate"
                         })
            except: pass

        # ── BASE YEAR BACKFILL (Fix for FRSH 2025 issue) ─────────────────────
        try:
            current_yr = datetime.datetime.now().year
            last_yr = current_yr - 1
            
            # Check if 2025 (or current - 1) is already in the list
            has_last_yr = any(str(last_yr) in str(e.get('period')) for e in eps_estimates)
            
            if not has_last_yr:
                eh = stock.earnings_history
                if eh is not None and not eh.empty:
                    # Filter for rows where the index (date) is in the last fiscal year
                    # For FRSH, Dec 2025 is the target.
                    actual_eps = 0.0
                    found_q = 0
                    
                    # Sort chronological to get the last 4 quarters
                    import pandas as _pd
                    sorted_eh = eh.sort_index(ascending=False)
                    for idx, row in sorted_eh.iterrows():
                        val = row.get('epsActual')
                        if val is not None and not _pd.isna(val):
                            actual_eps += float(val)
                            found_q += 1
                        if found_q >= 4: break
                    
                    if found_q >= 1: # We have some actuals
                        eps_estimates.insert(0, {
                            "period": f"FY {last_yr} (Actual)",
                            "avg": round(actual_eps, 2),
                            "status": "reported"
                        })
        except Exception as e:
            print(f"[Analyst] Base year backfill fail: {e}")

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
                
                # Fallback for rec_mean if yfinance info is missing it
                if not rec_mean:
                    total_votes = sum(rec_counts.values())
                    if total_votes > 0:
                        weighted_sum = (
                            rec_counts["strongBuy"] * 1 +
                            rec_counts["buy"] * 2 +
                            rec_counts["hold"] * 3 +
                            rec_counts["sell"] * 4 +
                            rec_counts["strongSell"] * 5
                        )
                        rec_mean = weighted_sum / total_votes
        except Exception:
            pass

        # ── Intuitive Sentiment & Median Calculation ──────────────────────────
        total_rec = sum(rec_counts.values())
        rec_sentiment = 0
        rec_median_label = "N/A"
        if total_rec > 0:
            # Score 0-100: SB=100, B=75, H=50, S=25, SS=0
            p = (rec_counts["strongBuy"] * 100) + (rec_counts["buy"] * 75) + \
                (rec_counts["hold"] * 50) + (rec_counts["sell"] * 25) + (rec_counts["strongSell"] * 0)
            rec_sentiment = round(p / total_rec, 2)
            
            # Median Analyst
            mid = total_rec / 2
            running = 0
            for k, label in [("strongBuy", "STRONG BUY"), ("buy", "BUY"), ("hold", "HOLD"), ("sell", "SELL"), ("strongSell", "STRONG SELL")]:
                running += rec_counts[k]
                if running >= mid:
                    rec_median_label = label
                    break
        elif rec_mean:
            # Fallback to inverse 1-5 mean if counts are missing
            rec_sentiment = round((5.0 - rec_mean) / 4.0 * 100, 2)
            # Rough label fallback
            if rec_mean <= 1.5: rec_median_label = "STRONG BUY"
            elif rec_mean <= 2.5: rec_median_label = "BUY"
            elif rec_mean <= 3.5: rec_median_label = "HOLD"
            elif rec_mean <= 4.5: rec_median_label = "SELL"
            else: rec_median_label = "STRONG SELL"

        # ── Historical Reported Data (EPS and Revenue) ───────────────────────────
        reported_eps = []
        reported_rev = []
        
        # Pre-compute fiscal year logic
        lfy_ts2 = info.get('lastFiscalYearEnd')
        if lfy_ts2:
            lfy_dt = datetime.datetime.fromtimestamp(lfy_ts2)
            fy_end_month = lfy_dt.month
            # Detect current fiscal year
            if datetime.datetime.now().month > fy_end_month:
                current_fy_num = datetime.datetime.now().year + 1
            else:
                current_fy_num = datetime.datetime.now().year
        else:
            fy_end_month = 12
            current_fy_num = datetime.datetime.now().year
            
        fy_start_month = (fy_end_month % 12) + 1
        
        def to_fiscal_label(dt):
            """Convert a date to standard fiscal label like 'Q1 2026'."""
            import pandas as _pd
            if not isinstance(dt, (_pd.Timestamp, datetime.datetime)):
                return str(dt)
            
            # Determine fiscal year
            if dt.month <= fy_end_month:
                fy = dt.year
            else:
                fy = dt.year + 1
            
            # Determine quarter
            # 0-indexed months from start of fiscal year
            months_since_start = (dt.month - fy_start_month) % 12
            fq = (months_since_start // 3) + 1
            return f"Q{fq} {fy}"
        
        try:
            # EPS History
            import pandas as _pd
            eh = stock.earnings_history
            if eh is not None and not eh.empty:
                for idx, row in eh.tail(4).iterrows(): # take up to last 4 reported
                    eps_act = row.get('epsActual') if hasattr(row, 'get') else None
                    eps_est = row.get('epsEstimate') if hasattr(row, 'get') else None
                    surprise_pct = row.get('surprisePercent') if hasattr(row, 'get') else None
                    
                    date_str = "--"
                    if isinstance(idx, (_pd.Timestamp, datetime.datetime)):
                        date_str = to_fiscal_label(idx)
                    elif idx:
                        date_str = str(idx)

                    val = float(eps_act) if eps_act is not None and not (isinstance(eps_act, float) and _pd.isna(eps_act)) else None
                    if val is not None:
                        reported_eps.append({
                            "period": date_str, "period_code": "reported", "avg": val * fx_rate, "status": "reported",
                            "surprise_pct": float(surprise_pct) if surprise_pct is not None and not _pd.isna(surprise_pct) else None
                        })
            
            # Revenue History - compute Y/Y growth and compare with estimates
            istmt = stock.quarterly_income_stmt
            import pandas as _pd
            if istmt is not None and not istmt.empty and 'Total Revenue' in istmt.index:
                rev_row = istmt.loc['Total Revenue']
                valid_cols = [c for c in rev_row.index if not _pd.isna(rev_row[c])]
                
                # Build a lookup: (fiscal_q, fiscal_year) -> revenue value
                rev_by_fq = {}
                for col_date in valid_cols:
                    if isinstance(col_date, (_pd.Timestamp, datetime.datetime)):
                        label = to_fiscal_label(col_date)
                        rev_by_fq[label] = float(rev_row[col_date])
                
                # Take latest 4 reported quarters (newest first in valid_cols, reverse for chronological)
                for col_date in list(valid_cols)[:4][::-1]: 
                    rev_act = float(rev_row[col_date])
                    
                    date_str = "--"
                    rev_growth = None
                    import pandas as _pd
                    if isinstance(col_date, (_pd.Timestamp, datetime.datetime)):
                        date_str = to_fiscal_label(col_date)
                        
                        # Compute Y/Y growth: find same fiscal quarter last year
                        # Parse the fiscal label we generated
                        parts = date_str.split()
                        if len(parts) == 2:
                            prev_label = f"{parts[0]} {int(parts[1]) - 1}"
                            prev_rev = rev_by_fq.get(prev_label)
                            if prev_rev and prev_rev > 0:
                                rev_growth = (rev_act - prev_rev) / prev_rev
                    
                    reported_rev.append({
                        "period": date_str, "period_code": "reported", "avg": rev_act * fx_rate, "status": "reported",
                        "growth": rev_growth,
                        "surprise_pct": None  # will be computed below if estimate data available
                    })
            
            # Try to compute revenue surprise for reported quarters
            # We compare actual revenue with the yearAgoRevenue * (1 + estimatedGrowth)
            # from the revenue_estimate data for each period
            try:
                rf_est = stock.revenue_estimate
                if rf_est is not None and not rf_est.empty:
                    for rr in reported_rev:
                        period_label = rr.get('period', '')
                        # Check if this reported Q matches a period in revenue estimates
                        # by comparing with yearAgoRevenue data
                        for est_idx, est_row in rf_est.iterrows():
                            est_label = labels.get(str(est_idx), str(est_idx))
                            if est_label == period_label:
                                # This estimate matches a reported Q - compute surprise
                                est_avg = est_row.get('avg')
                                if est_avg and not pd.isna(est_avg) and est_avg > 0:
                                    actual_rev = rr['avg'] / fx_rate if fx_rate != 1.0 else rr['avg']
                                    rr['surprise_pct'] = (actual_rev - float(est_avg)) / float(est_avg)
                                break
            except Exception as e_surp:
                print(f"[Analyst] Revenue surprise calc error: {e_surp}")
                
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
                    val_unscaled = float(avg) if avg is not None and not (isinstance(avg, float) and pd.isna(avg)) else None
                    try:
                        p_label = to_fiscal_label(pd.to_datetime(period_idx)) if isinstance(period_idx, (pd.Timestamp, datetime.datetime, str)) and any(c in str(period_idx) for c in ['-', '/', '.', '20']) else labels.get(p_key, p_key)
                    except:
                        p_label = labels.get(p_key, p_key)
                    
                    eps_estimates.append({
                        "period": p_label, 
                        "period_code": p_key,
                        "avg": val_unscaled * fx_rate if val_unscaled is not None else None,
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
                    val_unscaled = float(avg) if avg is not None and not (isinstance(avg, float) and pd.isna(avg)) else None
                    try:
                        p_label = to_fiscal_label(pd.to_datetime(period_idx)) if isinstance(period_idx, (pd.Timestamp, datetime.datetime, str)) and any(c in str(period_idx) for c in ['-', '/', '.', '20']) else labels.get(p_key, p_key)
                    except:
                        p_label = labels.get(p_key, p_key)
                    
                    rev_estimates.append({
                        "period": p_label, 
                        "period_code": p_key,
                        "avg": val_unscaled * fx_rate if val_unscaled is not None else None,
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

        # Determine if we even need the fallback.
        needs_nasdaq = len([e for e in eps_estimates if 'q' in e.get('period_code', '')]) < 4 or len([r for r in rev_estimates if 'q' in r.get('period_code', '')]) < 4
        if needs_nasdaq:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_nasdaq = executor.submit(fetch_nasdaq)
                n_data = future_nasdaq.result()
        
        if n_data:
            # Nasdaq EPS Quarters
            q_forecasts = n_data.get('data', {}).get('quarterlyForecast', {}).get('rows', [])
            for i, qf in enumerate(q_forecasts[:4]):
                p_code = "0q" if i == 0 else f"+{i}q"
                existing = next((e for e in eps_estimates if e.get('period_code') == p_code), None)
                avg = qf.get('consensusEPSForecast')
                if avg and avg != "N/A":
                    try:
                        avg_val = float(str(avg).replace('$', '').replace(',', ''))
                        period_lbl = labels.get(p_code, p_code)
                        if existing:
                            if not existing.get('avg'): existing['avg'] = avg_val
                            if existing.get('period') in ['Current Qtr', 'Next Qtr']: existing['period'] = period_lbl
                        else:
                            eps_estimates.append({"period": period_lbl, "period_code": p_code, "avg": avg_val, "growth": None, "status": "estimate"})
                    except: pass
            
            # Nasdaq Revenue Quarters
            r_forecasts = n_data.get('data', {}).get('revenueForecast', {}).get('rows', [])
            for i, rf in enumerate(r_forecasts[:4]):
                p_code = "0q" if i == 0 else f"+{i}q"
                existing = next((e for e in rev_estimates if e.get('period_code') == p_code), None)
                       # ── HISTORY MAPPING (for Y/Y Growth) ──────────────────────────────────
        history_eps = {}
        history_rev = {}
        try:
            # EPS History
            if stock.earnings_history is not None and not stock.earnings_history.empty:
                for date_idx, row in stock.earnings_history.iterrows():
                    lbl = to_fiscal_label(date_idx)
                    if lbl and not pd.isna(row.get('epsActual')):
                        history_eps[lbl] = float(row.get('epsActual'))
            
            # Revenue History (Quarterly)
            qf = stock.quarterly_financials
            if qf is not None and not qf.empty and "Total Revenue" in qf.index:
                rev_row = qf.loc["Total Revenue"]
                for date_idx, val in rev_row.items():
                    lbl = to_fiscal_label(date_idx)
                    if lbl and val is not None and not pd.isna(val):
                        history_rev[lbl] = float(val) / fx_rate # Adjust if stmt in different currency
            
            # Annual History (for FY growth)
            af = stock.financials
            if af is not None and not af.empty and "Total Revenue" in af.index:
                # Store annual rev by FY label
                rev_row = af.loc["Total Revenue"]
                for date_idx, val in rev_row.items():
                    # Standardize: last day of month X 20XX
                    fy_lbl = f"FY {date_idx.year if date_idx.month > fy_end_month else date_idx.year}"
                    if val is not None and not pd.isna(val) and fy_lbl not in history_rev:
                        history_rev[fy_lbl] = float(val) / fx_rate
            
            # Annual EPS from income statement (using Net Income / Shares or Diluted EPS)
            if af is not None and not af.empty and "Diluted EPS" in af.index:
                eps_row = af.loc["Diluted EPS"]
                for date_idx, val in eps_row.items():
                    fy_lbl = f"FY {date_idx.year if date_idx.month > fy_end_month else date_idx.year}"
                    if val is not None and not pd.isna(val):
                        history_eps[fy_lbl] = float(val)
        except Exception as he:
            print(f"[Analyst] History mapping error: {he}")

        # ── FINAL ASSEMBLY (6-Row Standard) ────────────────────────────────────
        current_year_str = str(current_fy_num)
        # Calculate exactly which quarter we are in now (1-4)
        now_dt = datetime.datetime.now()
        l_fy_yr = now_dt.year if now_dt.month > fy_end_month else now_dt.year - 1
        months_since_fye = (now_dt.year - l_fy_yr) * 12 + now_dt.month - fy_end_month
        this_q = ((months_since_fye - 1) // 3) + 1
        if this_q < 1: this_q = 1
        if this_q > 4: this_q = 4

        def fill_buckets(buckets, data_sources, target_fy):
            for source in data_sources:
                if not source: continue
                for item in source:
                    p = str(item.get('period', ''))
                    code = str(item.get('period_code', ''))
                    q_num = None
                    yr = None
                    is_fy = False
                    q_match = re.search(r'Q(\d)\s+(\d{4})', p)
                    fy_match = re.search(r'FY\s+(\d{4})', p) or re.search(r'FY\s+[A-Za-z]+\s+(\d{4})', p)
                    if q_match:
                        q_num = int(q_match.group(1)); yr = int(q_match.group(2))
                    elif fy_match:
                        digits = re.findall(r'\d{4}', p); yr = int(digits[-1]) if digits else None; is_fy = True
                    elif 'q' in code:
                        try:
                            rel_idx = int(code.replace('q', '').replace('+', ''))
                            q_num = ((this_q + rel_idx - 1) % 4) + 1
                            yr = target_fy if (this_q + rel_idx) <= 4 else target_fy
                        except: pass
                    elif 'y' in code:
                        try:
                            rel_idx = int(code.replace('y', '').replace('+', ''))
                            yr = target_fy + rel_idx; is_fy = True
                        except: pass

                    if yr == target_fy:
                        if not is_fy and q_num:
                            idx = f"Q{q_num}"
                            if buckets[idx]["avg"] is None or item.get('status') == 'reported':
                                buckets[idx].update({k: v for k, v in item.items() if v is not None})
                        elif is_fy:
                            if buckets["FY0"]["avg"] is None: buckets["FY0"].update({k: v for k, v in item.items() if v is not None})
                    elif yr == target_fy + 1 and is_fy:
                        if buckets["FY1"]["avg"] is None: buckets["FY1"].update({k: v for k, v in item.items() if v is not None})

        # Count reported items
        reported_eps_count = len([x for x in reported_eps if current_year_str in str(x.get('period'))])
        reported_rev_count = len([x for x in reported_rev if current_year_str in str(x.get('period'))])

        # Initialize
        eps_buckets = {f"Q{i}": {"period": f"Q{i} {current_fy_num}", "avg": None, "growth": None, "status": "estimate"} for i in range(1, 5)}
        eps_buckets.update({"FY0": {"period": f"FY {current_fy_num}", "avg": None, "growth": None, "reported_count": reported_eps_count}, 
                            "FY1": {"period": f"FY {current_fy_num + 1}", "avg": None, "growth": None}})
        rev_buckets = {f"Q{i}": {"period": f"Q{i} {current_fy_num}", "avg": None, "growth": None, "status": "estimate"} for i in range(1, 5)}
        rev_buckets.update({"FY0": {"period": f"FY {current_fy_num}", "avg": None, "growth": None, "reported_count": reported_rev_count}, 
                            "FY1": {"period": f"FY {current_fy_num + 1}", "avg": None, "growth": None}})

        fill_buckets(eps_buckets, [reported_eps + eps_estimates], current_fy_num)
        fill_buckets(rev_buckets, [reported_rev + rev_estimates], current_fy_num)

        # ── PLUG MISSING QUARTERS ──────────────────────────────────────────────
        # If 3 quarters and FY are present, calculate the 4th.
        def plug_missing_q(buckets):
            q_keys = ["Q1", "Q2", "Q3", "Q4"]
            missing = [q for q in q_keys if buckets[q].get("avg") is None]
            if len(missing) == 1 and buckets["FY0"].get("avg") is not None:
                m_key = missing[0]
                total = buckets["FY0"]["avg"]
                others = sum(buckets[q]["avg"] for q in q_keys if q != m_key and buckets[q].get("avg") is not None)
                buckets[m_key]["avg"] = round(total - others, 2)
                buckets[m_key]["status"] = "estimate" # It's a calculated estimate

        plug_missing_q(eps_buckets)
        plug_missing_q(rev_buckets)

        # ── REFINED GROWTH CALCULATION ──────────────────────────────────────────
        unified_eps = []; unified_rev = []
        
        # Improve FY0 baseline: yfinance info['trailingEps'] is often Adjusted
        actual_trailing_eps = info.get('trailingEps')
        actual_trailing_rev = info.get('totalRevenue')
        
        # Try to calculate FY-1 Actual by summing history (if all 4 qtrs present)
        # Note: prev_fy_lbl for ADBE FY 2026 is FY 2025
        prev_fy_lbl = f"FY {current_fy_num - 1}"
        
        # Revise history_eps[prev_fy_lbl] if trailingEps is better/available
        if actual_trailing_eps and prev_fy_lbl not in history_eps:
            history_eps[prev_fy_lbl] = actual_trailing_eps
        if actual_trailing_rev and prev_fy_lbl not in history_rev:
            history_rev[prev_fy_lbl] = actual_trailing_rev

        for k in ["Q1", "Q2", "Q3", "Q4", "FY0", "FY1"]:
            e = eps_buckets[k]; r = rev_buckets[k]
            if k.startswith("Q"):
                current_lbl = f"{k} {current_fy_num}"
                prev_lbl = f"{k} {current_fy_num - 1}"
            elif k == "FY0":
                current_lbl = f"FY {current_fy_num}"
                prev_lbl = f"FY {current_fy_num - 1}"
            else: # FY1
                current_lbl = f"FY {current_fy_num + 1}"
                prev_lbl = "FY0" # Sentinel for forward-comparison
            
            # Y/Y Growth
            if e.get("growth") is None and e.get("avg") is not None:
                if prev_lbl == "FY0":
                    past_val = eps_buckets["FY0"]["avg"]
                else:
                    past_val = history_eps.get(prev_lbl)
                
                if past_val and past_val != 0: 
                    e["growth"] = (e["avg"] / past_val) - 1
            
            if r.get("growth") is None and r.get("avg") is not None:
                if prev_lbl == "FY0":
                    past_val = rev_buckets["FY0"]["avg"]
                else:
                    past_val = history_rev.get(prev_lbl)
                
                if past_val and past_val != 0: 
                    r["growth"] = (r["avg"] / past_val) - 1
            
            e["period"] = current_lbl; r["period"] = current_lbl
            unified_eps.append(e); unified_rev.append(r)

        # ── EPS growth from estimates ─────────────────────────────────────────────
        eps_forward_growth = info.get('earningsGrowth', 0.10)
        eps_growth_5y_consensus = None
        try:
            ge = stock.growth_estimates
            if ge is not None and not ge.empty:
                target_labels = ['Next 5 Years', 'LTG']
                val = None
                for lbl in target_labels:
                    if lbl in ge.index:
                        val = ge.loc[lbl, ge.columns[0]]
                        if val is not None and not pd.isna(val): break
                if val is not None and not pd.isna(val):
                    eps_growth_5y_consensus = float(val)
        except: pass

        g_0y = None; g_1y = None
        for est in eps_estimates:
            if est.get('period_code') == '0y': g_0y = est.get('growth')
            if est.get('period_code') == '+1y': g_1y = est.get('growth')
        
        if g_0y is not None and g_0y > 0.02: eps_forward_growth = g_0y
        elif g_1y is not None: eps_forward_growth = g_1y
        elif g_0y is not None: eps_forward_growth = g_0y

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
                "sentiment": rec_sentiment,
                "median_label": rec_median_label,
                "counts": rec_counts
            },
            "eps_5yr_growth": eps_growth_5y_consensus if eps_growth_5y_consensus is not None else eps_forward_growth,
            "eps_growth_5y_consensus": eps_growth_5y_consensus,
            "eps_estimates":  unified_eps,
            "rev_estimates":  unified_rev
        }

    except Exception as e:
        import traceback
        print(f"[Analyst] Data fetch failed for {ticker_symbol}: {e}")
        print(traceback.format_exc())
        return {"ticker": ticker_symbol.upper(), "error": str(e)}
