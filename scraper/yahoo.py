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
_pd = pd
import re
import requests

def get_yahoo_analysis_normalized(ticker, info=None):
    """
    High-fidelity scraper for the Yahoo Finance 'Analysis' tab.
    Extracts Normalized (Non-GAAP) Estimates and Year-Ago Anchors for EPS and Revenue.
    v267: Direct HTML Table Parsing (Robust against Yahoo SSR changes)
    """
    res = {'eps': {}, 'rev': {}}
    t_upper = ticker.upper() if isinstance(ticker, str) else str(ticker).upper()
    
    def parse_n(val):
        if not val: return 0.0
        val = str(val).replace('$', '').replace(',', '').strip()
        mult = 1.0
        if 'B' in val: mult = 1e9; val = val.replace('B', '')
        elif 'M' in val: mult = 1e6; val = val.replace('M', '')
        elif '%' in val: val = val.replace('%', '')
        try: return float(val) * mult
        except: return 0.0

    try:
        # 1. Preliminary fetch from info (Fastest)
        if info:
            try:
                res['eps']['0y'] = {'avg': float(info.get('epsCurrentYear', 0))}
                res['eps']['+1y'] = {'avg': float(info.get('forwardEps') or info.get('epsForward') or 0)}
            except: pass

        # 2. Forensic Scrape for the full Truth Table
        url = f"https://finance.yahoo.com/quote/{t_upper}/analysis"
        # v265: Force Googlebot UA for Forensic Scrapes to bypass Yahoo Consent (Guce)
        headers = {'User-Agent': "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            html = response.text
            
            # v267: Direct HTML Table Parsing
            tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
            for table in tables:
                rows = re.findall(r'<tr.*?</tr>', table, re.DOTALL)
                for row in rows:
                    clean_row = re.sub(r'<[^>]+>', ' ', row).strip()
                    
                    if 'Avg. Estimate' in clean_row:
                        m0 = re.search(r'data-testid-cell="0y".*?>\s*([^<]+)', row)
                        m1 = re.search(r'data-testid-cell="\+1y".*?>\s*([^<]+)', row)
                        val0 = m0.group(1).strip() if m0 else None
                        val1 = m1.group(1).strip() if m1 else None
                        
                        # Determine if Revenue (B/M) or EPS (decimal)
                        is_rev = (val0 and ('B' in val0 or 'M' in val0)) or (val1 and ('B' in val1 or 'M' in val1))
                        
                        if is_rev:
                            if val0: res['rev']['0y'] = {'avg': parse_n(val0)}
                            if val1: res['rev']['+1y'] = {'avg': parse_n(val1)}
                        else:
                            if val0: res['eps']['0y'] = {'avg': parse_n(val0)}
                            if val1: res['eps']['+1y'] = {'avg': parse_n(val1)}
                            
                    elif 'Year Ago EPS' in clean_row:
                        m_ya = re.search(r'data-testid-cell="0y".*?>\s*([^<]+)', row)
                        if m_ya:
                            ya_val = parse_n(m_ya.group(1).strip())
                            if '0y' not in res['eps']: res['eps']['0y'] = {}
                            res['eps']['0y']['yearAgo'] = ya_val # Use 'yearAgo' to match engine expectation
                            
                    elif 'Year Ago Sales' in clean_row:
                        m_ya = re.search(r'data-testid-cell="0y".*?>\s*([^<]+)', row)
                        if m_ya:
                            ya_val = parse_n(m_ya.group(1).strip())
                            if '0y' not in res['rev']: res['rev']['0y'] = {}
                            res['rev']['0y']['yearAgo'] = ya_val

            # v276: Priority Truth Pass (Non-GAAP takes precedence)
            for trend_key in ["revenueTrend", "earningsTrend", "earningsTrendNonGaap"]:
                parts = html.split(f'"{trend_key}"')
                if len(parts) < 2: parts = html.split(f'\\"{trend_key}\\"')
                if len(parts) < 2: continue
                
                chunk = parts[1][:150000]
                is_nongaap = (trend_key == "earningsTrendNonGaap")
                
                for p in ['0y', '+1y']:
                    p_target = f'"{p}"'
                    if p_target not in chunk: p_target = f'\\"{p}\\"'
                    if p_target not in chunk: continue 
                    
                    p_idx = chunk.find(p_target)
                    sub_chunk = chunk[p_idx:p_idx+3000] 
                    
                    eps_avg_m = re.search(r'earningsEstimate.*?avg.*?raw.*?([\d\.\-]+)', sub_chunk)
                    eps_ya_m = re.search(r'yearAgoEps.*?raw.*?([\d\.\-]+)', sub_chunk)
                    
                    if eps_avg_m:
                        val = float(eps_avg_m.group(1))
                        if p not in res['eps']: res['eps'][p] = {}
                        # v276: NonGaap overwrites anything. Others only fill gaps.
                        if is_nongaap or 'avg' not in res['eps'][p]:
                            res['eps'][p]['avg'] = val
                    
                    if eps_ya_m:
                        val = float(eps_ya_m.group(1))
                        if p not in res['eps']: res['eps'][p] = {}
                        if is_nongaap or 'yearAgo' not in res['eps'][p]:
                            res['eps'][p]['yearAgo'] = val

                    # Revenue extraction
                    rev_avg_m = re.search(r'revenueEstimate.*?avg.*?raw.*?([\d\.\-]+)', sub_chunk)
                    rev_ya_m = re.search(r'yearAgoSales.*?raw.*?([\d\.\-]+)', sub_chunk)
                    
                    if rev_avg_m:
                        if p not in res['rev']: res['rev'][p] = {}
                        if 'avg' not in res['rev'][p]:
                            res['rev'][p]['avg'] = float(rev_avg_m.group(1))
                    if rev_ya_m:
                        if p not in res['rev']: res['rev'][p] = {}
                        if 'yearAgo' not in res['rev'][p]:
                            res['rev'][p]['yearAgo'] = float(rev_ya_m.group(1))

            # v260: Price Target Scraping
            match_pt = re.search(r'"targetMeanPrice":\{"raw":([\d\.\-]+)', html)
            if match_pt: res['target_mean'] = float(match_pt.group(1))
            match_pt_low = re.search(r'"targetLowPrice":\{"raw":([\d\.\-]+)', html)
            if match_pt_low: res['target_low'] = float(match_pt_low.group(1))
            match_pt_high = re.search(r'"targetHighPrice":\{"raw":([\d\.\-]+)', html)
            if match_pt_high: res['target_high'] = float(match_pt_high.group(1))
            match_pt_median = re.search(r'"targetMedianPrice":\{"raw":([\d\.\-]+)', html)
            if match_pt_median: res['target_median'] = float(match_pt_median.group(1))

        # Nasdaq Fallback for EPS Anchor (Only if Yahoo Truth is missing)
        if 'yearAgo' not in res['eps'].get('0y', {}):
            nasdaq_anchor = get_nasdaq_actual_eps(t_upper)
            if nasdaq_anchor:
                if '0y' not in res['eps']: res['eps']['0y'] = {}
                res['eps']['0y']['yearAgo'] = nasdaq_anchor
                log(f"DEBUG: v258 Nasdaq Truth injected into Analysis Anchor for {t_upper}: {nasdaq_anchor}")

    except Exception as e:
        print(f"Error scraping Yahoo Analysis for {t_upper}: {e}")
    
    return res
try:
    from utils.kv import kv_get, kv_set
except ImportError:
    try:
        from ..utils.kv import kv_get, kv_set
    except ImportError:
        try:
            from api.utils.kv import kv_get, kv_set
        except ImportError:
            def kv_get(k): return None
            def kv_set(k, v, ex=None): return False

def log(*args, **kwargs):
    print(*args, **kwargs)

USER_AGENTS = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
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

def find_nearest_col(df, target_date, max_days=10):
    """Finds the column index in df that most closely matches target_date within max_days."""
    if df is None or df.empty or target_date is None:
        return None
    
    # Normalize target_date to a date-only object for robust comparison
    try:
        if isinstance(target_date, str):
            target_dt = pd.to_datetime(target_date).date()
        elif hasattr(target_date, 'date'):
            target_dt = target_date.date()
        else:
            target_dt = pd.to_datetime(target_date).date()
    except:
        return None
        
    best_col = None
    min_delta = 9999
    
    for col in df.columns:
        try:
            # Handle Datetime, Timestamp, or Strings
            if hasattr(col, 'date'):
                col_dt = col.date()
            else:
                col_dt = pd.to_datetime(col).date()
                
            delta = abs((col_dt - target_dt).days)
            if delta < min_delta and delta <= max_days:
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

def get_nasdaq_comprehensive_estimates(ticker: str, force_refresh: bool = False) -> dict:
    """ Fetches yearly and quarterly EPS AND Revenue estimates from Nasdaq in parallel. """
    ticker = ticker.upper()
    cache_key = f"nq_comp_v2_{ticker}"
    
    if not force_refresh:
        cached = kv_get(cache_key)
        if cached: return cached

    results = {"yearly_eps": [], "quarterly_eps": [], "yearly_rev": [], "quarterly_rev": []}
    
    def fetch_url(url_type, t_sym):
        endpoint = "earnings-forecast" if url_type == "eps" else "revenue-forecast"
        try:
            url = f'https://api.nasdaq.com/api/analyst/{t_sym}/{endpoint}'
            headers = {'User-Agent': get_random_agent()}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
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

def get_yahoo_eps_trend(ticker: str) -> dict:
    """Fetches EPS Trend data (Current, 7 Days Ago, etc.) from Yahoo Finance."""
    # v206: Try yfinance High-Fidelity Fallback first for Estimates/Trends
    try:
        stock = yf.Ticker(ticker)
        ee = getattr(stock, 'earnings_estimate', None)
        if ee is not None and not ee.empty:
            mapping = {}
            for period in ['0y', '+1y', '+2y', '0q', '+1q']:
                if period in ee.index:
                    row = ee.loc[period]
                    mapping[period] = {
                        'avg': row.get('avg'),
                        'low': row.get('low'),
                        'high': row.get('high'),
                        'yearAgoEps': row.get('yearAgoEps'),
                        'numberOfAnalysts': row.get('numberOfAnalysts'),
                        'growth': row.get('growth'),
                        # compatibility fields for older code paths
                        'current': row.get('avg')
                    }
            if mapping:
                return mapping
    except: pass

    try:
        # Use query2 which is often more reliable
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=earningsTrend"
        headers = {
            'User-Agent': get_random_agent(),
            'Accept': 'application/json',
            'Referer': 'https://finance.yahoo.com/quote/' + ticker
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
             # Fallback to query1
             url = url.replace('query2', 'query1')
             resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code != 200:
             print(f"DEBUG: Yahoo EPS Trend Fetch failed for {ticker} ({resp.status_code})")
             return {}

        data = resp.json()
        trends = data.get('quoteSummary', {}).get('result', [{}])[0].get('earningsTrend', {}).get('trend', [])
        
        mapping = {}
        for t in trends:
            p = t.get('period') # e.g. "0y", "+1y", "0q"
            if p:
                mapping[p] = {
                    'avg': t.get('earningsEstimate', {}).get('avg', {}).get('raw'),
                    'low': t.get('earningsEstimate', {}).get('low', {}).get('raw'),
                    'high': t.get('earningsEstimate', {}).get('high', {}).get('raw'),
                    'yearAgoEps': t.get('earningsEstimate', {}).get('yearAgoEps', {}).get('raw'),
                    'numberOfAnalysts': t.get('earningsEstimate', {}).get('numberOfAnalysts', {}).get('raw'),
                    'growth': t.get('earningsEstimate', {}).get('growth', {}).get('raw'),
                    # compatibility fields
                    'current': t.get('current', {}).get('raw')
                }
        return mapping
    except Exception as e:
        print(f"ERROR: get_yahoo_eps_trend for {ticker}: {e}")
        return {}

def get_nasdaq_historical_eps(ticker: str) -> list:
    """Fetch quarterly Adjusted (Non-GAAP) EPS from Nasdaq Surprise API."""
    try:
        url = f"https://api.nasdaq.com/api/company/{ticker.upper()}/earnings-surprise"
        # v92: Enhanced headers for deeper penetration
        headers = {
            'User-Agent': get_random_agent(),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.nasdaq.com',
            'Referer': 'https://www.nasdaq.com/'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            rows = data.get('data', {}).get('earningsSurpriseTable', {}).get('rows', [])
            result = []
            now = datetime.datetime.now()
            for row in rows:
                try:
                    dt_str = row.get('dateReported')
                    if not dt_str: continue
                    dt = datetime.datetime.strptime(dt_str, '%m/%d/%Y')
                    
                    # Skip future dates (estimates) in the surprise table
                    if dt > now + datetime.timedelta(days=1): continue
                    
                    val = row.get('eps') or row.get('actualEPS')
                    if val is not None:
                        clean_val = str(val).replace('$', '').replace(',', '').strip()
                        if clean_val and clean_val.upper() != "N/A":
                            eps = float(clean_val)
                            result.append({"date": dt, "eps": eps})
                except: continue
            return result
    except Exception as e:
        log(f"Error fetching Nasdaq Historical Adj EPS for {ticker}: {e}")
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
    Calculates the arithmetic mean of the YoY growth rates for the next 3 years.
    """
    if not trailing_eps or trailing_eps <= 0:
        return None
    try:
        # Optimization: Use the comprehensive fetcher
        nq_data = get_nasdaq_comprehensive_estimates(ticker)
        rows = nq_data.get("yearly_eps", [])
        if not rows: return None
        
        # We also need a clean Non-GAAP base for accurate YoY growth
        actual_eps_base = None
        try:
            # We call the companion function to get the sum of last 4 quarters (Non-GAAP)
            actual_eps_base = get_nasdaq_actual_eps(ticker)
        except:
            pass
            
        base_eps = actual_eps_base if actual_eps_base and actual_eps_base > 0 else trailing_eps
        
        # Collect base + up to 3 years of forecasts
        eps_values = [base_eps]
        for row in rows[:3]:
            val = safe_nasdaq_float(row.get('consensusEPSForecast'))
            if val is not None and val > 0:
                eps_values.append(val)
        
        if len(eps_values) < 2: return None
        
        # Calculate individual YoY growths
        growths = []
        for i in range(1, len(eps_values)):
            prev = eps_values[i-1]
            curr = eps_values[i]
            if prev > 0:
                growth = (curr - prev) / prev
                # Clamp extreme growth rates to avoid skewing the average too much
                clamped_growth = min(max(growth, -0.5), 1.5)
                growths.append(clamped_growth)
        
        if not growths: return None
        
        # Return arithmetic mean of the growth rates
        return sum(growths) / len(growths)

    except Exception as e:
        log(f"Error fetching Nasdaq growth for {ticker}: {e}")
    return None

def get_nasdaq_actual_eps(ticker: str) -> float:
    """
    Fetches the actual Adjusted (Non-GAAP) EPS for the last 4 quarters from Nasdaq.
    Sums them to provide a more accurate 'Trailing EPS' for companies with large GAAP vs Non-GAAP gaps.
    v255: Added Forensic Neutralizer (Comparing Actual vs Consensus to scrub GAAP outliers).
    """
    try:
        url = f'https://api.nasdaq.com/api/company/{ticker.upper()}/earnings-surprise'
        # v163: Reduced timeout to 4s to prevent Vercel 500 timeouts
        req = urllib.request.Request(url, headers={'User-Agent': get_random_agent()})
        with urllib.request.urlopen(req, timeout=4) as response:
            raw_data = response.read()
            data = json.loads(raw_data)
            
        if data and data.get('data'):
            rows = data['data'].get('earningsSurpriseTable', {}).get('rows', [])
            if rows:
                total_eps = 0.0
                # Sum the last 4 reported quarters
                count = 0
                for row in rows[:4]:
                    # 'eps' is the actual reported EPS in the surprise table
                    val_str = row.get('eps') or row.get('actualEPS')
                    fc_str = row.get('consensusForecast')
                    if val_str:
                        try:
                            val = float(val_str)
                            
                            # Forensic Neutralization: If Actual differs significantly from Consensus, 
                            # it's often a GAAP-driven distortion (e.g. UBER tax benefit).
                            if fc_str:
                                try:
                                    f_fc = float(fc_str)
                                    if f_fc != 0:
                                        diff = abs(val - f_fc)
                                        # Threshold 25% or $0.15 matches the logic in get_company_data
                                        if (diff / abs(f_fc) > 0.25) or diff > 0.15:
                                            log(f"DEBUG: v255 Nasdaq Forensic Neutralizer for {ticker} ({val} -> {f_fc})")
                                            val = f_fc
                                except: pass
                            
                            total_eps += val
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

def get_period_labels(ticker_info: dict, historical_data: dict = None, current_fy: int = None) -> dict:
    """
    Returns a mapping for relative period codes based on the company's fiscal year.
    Standardizes on 'FY 20XX' and relative quarters.
    """
    try:
        now = datetime.datetime.now()
        if current_fy is None:
            lfy_ts = ticker_info.get('lastFiscalYearEnd')
            if not lfy_ts:
                current_fy = now.year if now.month <= 12 else now.year + 1
            else:
                lfy_dt = datetime.datetime.fromtimestamp(lfy_ts)
                fy_end_month = lfy_dt.month
                if now.month > fy_end_month:
                    current_fy = now.year + 1
                else:
                    current_fy = now.year
            
            # v152: Synchronize with history if available
            if historical_data and "years" in historical_data:
                try:
                    hist_years = [int(y) for y in historical_data["years"] if str(y).isdigit()]
                    if hist_years:
                        max_hist = max(hist_years)
                        if current_fy <= max_hist:
                            current_fy = max_hist + 1
                except: pass



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

def fetch_latest_news_v2(ticker_symbol: str) -> list:
    """Fetches several recent news headlines for the ticker."""
    try:
        stock = yf.Ticker(ticker_symbol)
        news = stock.news
        if news and len(news) > 0:
            results = []
            for item in news[:4]:  # Top 4 news items
                # yfinance news uses a nested 'content' structure
                content = item.get('content', item) if isinstance(item, dict) else {}
                title = content.get('title', 'N/A')
                provider = content.get('provider', {})
                publisher = provider.get('displayName', 'N/A') if isinstance(provider, dict) else str(provider)
                
                # Fallback to older yfinance schema if needed
                if title == 'N/A' and item.get('title'):
                    title = item.get('title', 'N/A')
                    publisher = item.get('publisher', 'N/A')
                    
                results.append(f"{title} (Source: {publisher})")
            return results
    except Exception as e:
        print(f"Error fetching news for {ticker_symbol}: {e}")
    return ["No significant recent news available (last 24-48h)."]


def get_company_synthesis(ticker: str, info: dict) -> str:
    """
    Returns a professional, structured analytical synthesis of the company in English.
    Focuses on business model, competitive advantages, and risk profile.
    """
    ticker_upper = ticker.upper()
    name = info.get('longName') or ticker_upper
    sector = info.get('sector', 'N/A')
    industry = info.get('industry', 'N/A')
    summary = info.get('longBusinessSummary', '')

    # 1. Executive Summary & Core Activity
    presentation = f"{name} is a leading enterprise operating within the {sector} sector, with a primary focus on {industry}."
    if summary:
        # Extract first 2-3 sentences for a professional description
        sentences = re.split(r'(?<=[.!?])\s+', summary)
        activity = " ".join(sentences[:3])
    else:
        activity = f"The company operates a global industrial footprint, providing specialized solutions and integrated services within the {industry} domain."

    # 2. Strategic Strengths & Competitive Moats
    strengths = []
    weaknesses = []

    # Financial Performance & Growth
    rev_growth = info.get('revenueGrowth')
    if rev_growth and rev_growth > 0.15: 
        strengths.append(f"Robust revenue expansion (YoY: {rev_growth*100:.1f}%) indicating strong market demand.")
    elif rev_growth and rev_growth < 0: 
        weaknesses.append("Observed revenue contraction suggesting cyclical headwinds or market share pressure.")

    # Profitability & Efficiency
    margin = info.get('profitMargins')
    if margin and margin > 0.20: 
        strengths.append(f"High-margin operations (Net Margin: {margin*100:.1f}%), reflecting pricing power or operational scale.")
    elif margin and margin < 0.05: 
        weaknesses.append("Lean profit margins, potentially susceptible to input cost volatility.")

    # Capital Structure
    debt_equity = info.get('debtToEquity')
    if debt_equity and debt_equity < 40: 
        strengths.append("Conservative capital structure with low leverage, providing significant financial flexibility.")
    elif debt_equity and debt_equity > 150: 
        weaknesses.append("Elevated debt-to-equity ratio, increasing sensitivity to interest rate fluctuations.")

    # Market Valuation Context
    pe = info.get('trailingPE')
    if pe and pe < 18: 
        strengths.append(f"Attractive valuation relative to historical norms (P/E: {pe:.1f}x).")
    elif pe and pe > 45: 
        weaknesses.append(f"Premium valuation (P/E: {pe:.1f}x), necessitating aggressive growth to justify current levels.")

    # Defaults for completeness
    if not strengths: strengths.append("Established market presence with diversified revenue streams.")
    if not weaknesses: weaknesses.append("Exposure to broader macroeconomic cycles and regulatory shifts.")

    # 3. Market Intelligence & Recent Developments
    news_items = fetch_latest_news_v2(ticker_upper)
    
    # 4. Construct Structured Output
    output = f"**EXECUTIVE SUMMARY**\n{presentation}\n\n{activity}\n\n"
    output += f"**STRATEGIC STRENGTHS**\n" + "\n".join([f"• {s}" for s in strengths[:3]]) + "\n\n"
    output += f"**VULNERABILITIES & RISKS**\n" + "\n".join([f"• {w}" for w in weaknesses[:3]]) + "\n\n"
    output += f"**LATEST MARKET INTELLIGENCE**\n" + "\n".join([f"• {n}" for n in news_items])

    return output


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
    historic_eps_growth = None
    historic_fcf_growth = None
    historic_buyback_rate = None
    red_flags = []
    historical_trends = []
    historical_data = {
        "years": [], "revenue": [], "eps": [], "diluted_eps": [], "fcf": [], "shares": []
    }
    history_eps = {}
    history_rev = {}
    peg_ratio = None

    try:
        # --- ATTEMPT 1: yf.Ticker.info (Primary) ---
        stock = yf.Ticker(ticker_symbol)
        
        # Parallelize data fetching
        try:
            info = stock.info
            # v163: Ticker transition recovery (FI -> FISV) - yfinance returns 404 for FI currently
            if (not info or not info.get('symbol')) and ticker_symbol.upper() == 'FI':
                stock = yf.Ticker('FISV')
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
                # Increased timeout to 10s as Nasdaq can be slow
                nasdaq_growth_3y = future_nasdaq_cagr.result(timeout=10)
                nasdaq_actual_eps = future_nasdaq_actual.result(timeout=10)
            except Exception as e:
                log(f"DEBUG: Nasdaq growth result timeout/fail: {e}")
                pass

        # Detect Nasdaq Actual (Non-GAAP)
        if nasdaq_actual_eps is not None:
            # Store separately instead of overwriting the main trailing_eps
            # This allow the UI to show the GAAP value the user expects from Yahoo summary
            adjusted_eps = nasdaq_actual_eps
        else:
            adjusted_eps = trailing_eps

        # --- GROWTH SELECTION (v148: Yahoo Forward Estimates Priority) ---
        # Priority 1: Yahoo's own forward-year growth from earnings_estimate (Non-GAAP consensus)
        # This directly uses the analyst consensus growth rates Yahoo computes.
        yf_0y_growth = None
        yf_1y_growth = None
        try:
            ee = stock.earnings_estimate
            if ee is not None and not ee.empty:
                for idx, row in ee.iterrows():
                    g = row.get('growth')
                    if g is not None and not pd.isna(g):
                        if str(idx) == '0y': yf_0y_growth = float(g)
                        elif str(idx) == '+1y': yf_1y_growth = float(g)
        except: pass

        # Select the best available growth rate
        # v219: Always use the arithmetic mean of FY0 + FY1 growth for a balanced estimate
        if yf_0y_growth is not None and yf_1y_growth is not None:
            eps_growth = (yf_0y_growth + yf_1y_growth) / 2
            eps_growth_period = "Avg FY0+FY1 Growth (Yahoo Consensus)"
        elif yf_0y_growth is not None and yf_0y_growth > 0.02:
            eps_growth = yf_0y_growth
            eps_growth_period = "Current FY Growth (Yahoo Consensus)"
        elif yf_1y_growth is not None and yf_1y_growth > 0:
            eps_growth = yf_1y_growth
            eps_growth_period = "Next FY Growth (Yahoo Consensus)"
        elif eps_growth_5y_consensus and eps_growth_5y_consensus > 0:
            eps_growth = eps_growth_5y_consensus
            eps_growth_period = "Next 5 Years (Consensus)"
        elif nasdaq_growth_3y and nasdaq_growth_3y > 0:
            eps_growth = nasdaq_growth_3y
            eps_growth_period = "3Y Avg Growth (Nasdaq)"
            
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
                    # Parallelize core financial fetches to stay under 5-10s
                    future_fin = future_fin # already submitted
                    future_qfin = executor.submit(lambda: getattr(stock, 'quarterly_financials', {}))
                    future_cf = executor.submit(lambda: getattr(stock, 'cashflow', {}))
                    future_qcf = executor.submit(lambda: getattr(stock, 'quarterly_cashflow', {}))
                    future_bs = executor.submit(lambda: getattr(stock, 'balance_sheet', {}))
                    future_qbs = executor.submit(lambda: getattr(stock, 'quarterly_balance_sheet', {}))
                    future_div = executor.submit(lambda: getattr(stock, 'dividends', pd.Series()))
                    
                    financials = future_fin.result(timeout=10)
                    q_financials = future_qfin.result(timeout=10)
                    cashflow = future_cf.result(timeout=10)
                    q_cashflow = future_qcf.result(timeout=10)
                    bs = future_bs.result(timeout=10)
                    q_bs = future_qbs.result(timeout=10)
                    dividends_raw = future_div.result(timeout=10)
                else:
                    financials = getattr(stock, 'financials', {})
                    q_financials = getattr(stock, 'quarterly_financials', {})
                    cashflow = getattr(stock, 'cashflow', {})
                    q_cashflow = getattr(stock, 'quarterly_cashflow', {})
                    bs = getattr(stock, 'balance_sheet', {})
                    q_bs = getattr(stock, 'quarterly_balance_sheet', {})
                    dividends_raw = getattr(stock, 'dividends', pd.Series())
            except Exception as e:
                log(f"DEBUG: Financials fetch error: {e}")
                financials = financials or {}
                cashflow = cashflow or {}
                bs = bs or {}
                q_bs = q_bs or {}
                dividends_raw = dividends_raw if not dividends_raw.empty else pd.Series()
            
            if executor is not None:
                executor.shutdown(wait=False)
            
            # Massive speedups: No longer awaiting qfin, qcf, or heavy dividends histories.

        # v201: Baseline adjusted_eps (will be refined later)
        adjusted_eps = trailing_eps
        # v206: Prioritize Live/Refined Shares (Significant for massive buyback companies like AAPL)
        shares_outstanding = info.get('impliedSharesOutstanding') or info.get('sharesOutstanding') or 0
        
        if not shares_outstanding and financials is not None and not financials.empty:
            for k in ['Diluted Average Shares', 'Basic Average Shares']:
                idx = find_idx(financials, k)
                if idx:
                    try:
                        val_obj = financials.loc[idx]
                        val = float(val_obj.iloc[0]) if hasattr(val_obj, 'iloc') else float(val_obj)
                        if val > 0:
                            shares_outstanding = val
                            break
                    except: pass
            if not shares_outstanding:
                try: 
                    cf_shares = stock.fast_info.get('shares_outstanding')
                    if cf_shares: shares_outstanding = float(cf_shares)
                except: pass



        # ── GAAP EPS RECALIBRATION (runs AFTER financials are resolved) ──
        # Now that we have the actual income statement, calculate GAAP EPS
        # and recalibrate P/E if it differs significantly from the info-tag version
        if not fast_mode and financials is not None:
            try:
                if not financials.empty:
                    ni_idx = find_idx(financials, 'Net Income Common Stock Holders')
                    if not ni_idx: ni_idx = find_idx(financials, 'Net Income')
                    
                    if ni_idx and shares_outstanding and shares_outstanding > 0:
                        ni_obj = financials.loc[ni_idx]
                        net_inc = float(ni_obj.iloc[0]) if hasattr(ni_obj, 'iloc') else float(ni_obj)
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
                    fcf_obj = cashflow.loc[fcf_idx]
                    fcf = float(fcf_obj.iloc[0]) if hasattr(fcf_obj, 'iloc') else float(fcf_obj)
                else:
                    ocf_idx = find_idx(cashflow, 'Operating Cash Flow')
                    if ocf_idx:
                        ocf_obj = cashflow.loc[ocf_idx]
                        fcf = float(ocf_obj.iloc[0]) if hasattr(ocf_obj, 'iloc') else float(ocf_obj)
        except: pass
        
        if fcf is None:
            fcf = info.get('freeCashflow')
            if fcf is None: fcf = info.get('operatingCashflow')
        # shares_outstanding already computed above
        
        # --- STRICT MAPPING (v171: LEVERAGE & LIQUIDITY) ---
        # Rule: Total Debt = LT Debt + ST Debt (Interest Bearing Only). EXCLUDE Leases.
        def get_strict_debt(df):
            if df is None or df.empty: return 0
            
            def get_latest_valid(row_names):
                if not row_names: return 0
                for name in row_names:
                    idx = find_idx(df, name)
                    if idx is not None:
                        series = df.loc[idx]
                        if isinstance(series, pd.Series):
                            valid = series.dropna()
                            if not valid.empty: return float(valid.iloc[0])
                        else:
                            if not pd.isna(series): return float(series)
                return 0

            # Rule: Sum interest-bearing components ONLY
            lt = get_latest_valid(['Long Term Debt', 'Total Long Term Debt'])
            st = get_latest_valid(['Current Debt', 'Short Term Debt', 'Short Long Term Debt', 'Commercial Paper'])
            return (lt + st)
            
        td_raw = get_strict_debt(q_bs) or get_strict_debt(bs)
        
        # v171: Fallback only if strict mapping results in 0, but check against info['totalDebt']
        # to ensure we aren't using a bloated figure that includes leases.
        info_debt = (info.get('totalDebt') or 0) * fx_rate
        if td_raw > 0:
            total_debt = td_raw * fx_rate
        else:
            total_debt = info_debt
        
        # Sanity Check (v168): Debt cannot exceed Total Liabilities (Quantitative Guardrail)
        total_liab = (info.get('totalLiabilitiesNetMinorityInterest') or info.get('totalLiabilities') or 0)
        if (total_debt >= total_liab) and total_liab > 0:
            print(f"CRITICAL DASHBOARD ERROR: Debt (${total_debt/1e9:.1f}B) >= Liabilities (${total_liab/1e9:.1f}B). Quantitative sanity check failed. Reverting to strict LT+ST mapping.")
            total_debt = td_raw * fx_rate

        total_cash = (info.get('totalCash') or 0) * fx_rate

        gross_margins = info.get('grossMargins') # Ratio
        profit_margins = info.get('profitMargins') # Ratio
        
        revenue = None
        try:
            if financials is not None and not financials.empty:
                rev_idx = find_idx(financials, 'Total Revenue')
                if rev_idx:
                    rev_obj = financials.loc[rev_idx]
                    revenue = float(rev_obj.iloc[0]) if hasattr(rev_obj, 'iloc') else float(rev_obj)
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

        # v168: Strict Current Ratio (Total Current Assets / Total Current Liabilities)
        def get_cr(df):
            if df is None or df.empty: return None
            ca_idx = find_idx(df, 'Total Current Assets')
            cl_idx = find_idx(df, 'Current Liabilities') or find_idx(df, 'Total Current Liabilities')
            if ca_idx and cl_idx:
                ca_obj = df.loc[ca_idx]
                ca = float(ca_obj.iloc[0]) if hasattr(ca_obj, 'iloc') else float(ca_obj)
                cl_obj = df.loc[cl_idx]
                cl = float(cl_obj.iloc[0]) if hasattr(cl_obj, 'iloc') else float(cl_obj)
                return (ca / cl) if cl > 0 else None
            return None
            
        current_ratio = get_cr(q_bs) or get_cr(bs) or info.get('currentRatio')
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
        try:
            if dividend_yield is not None:
                dividend_yield = float(dividend_yield)
        except:
            dividend_yield = None
            
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
                    fcf_obj = cashflow.loc[fcf_idx]
                    fcf_y = fcf_obj.dropna().head(5).tolist() if hasattr(fcf_obj, 'dropna') else [fcf_obj]
                else:
                    ocf_idx = find_idx(cashflow, 'Operating Cash Flow')
                    if ocf_idx:
                        ocf_obj = cashflow.loc[ocf_idx]
                        fcf_y = ocf_obj.dropna().head(5).tolist() if hasattr(ocf_obj, 'dropna') else [ocf_obj]
                
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
        operating_cashflow = fcf # Default to FCF
        try:
            if cashflow is not None and not cashflow.empty:
                ocf_idx = find_idx(cashflow, 'Operating Cash Flow')
                if ocf_idx:
                    # Get the most recent column (usually TTM or last FY)
                    ocf_obj = cashflow.loc[ocf_idx]
                    operating_cashflow = float(ocf_obj.iloc[0]) if hasattr(ocf_obj, 'iloc') else float(ocf_obj)
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
                            # v206: Strict Consecutive Year Check (Prevents skipping breaks like AAPL 1995-2012)
                            if curr_yr - 1 == prev_yr and div_annual[curr_yr] >= div_annual[prev_yr] * 0.98: 
                                current_streak += 1
                            else:
                                break
                    dividend_streak = current_streak + (1 if current_streak > 0 else 0) # Add anchor year
                    
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
            "diluted_eps": [],
            "fcf": [],
            "shares": []
        }
        
        # --- PHASE 0: PRE-CALCULATE NON-GAAP (ADJUSTED) EPS HISTORY ---
        # v87: Hyper-Robust Unified Aggregation (YF + Nasdaq)
        adjusted_history = {}
        try:
            import pandas as _pd
            raw_data_map = {} # {year_str: {date_str: val}}
            
            # v95: Determine Fiscal Year End Month for correct mapping
            fy_end_month = 12
            try:
                fye = info.get('fiscalYearEndMonth')
                if fye: fy_end_month = int(fye)
                else:
                    last_fye = info.get('lastFiscalYearEnd')
                    if last_fye:
                        fy_end_month = datetime.datetime.fromtimestamp(last_fye).month
            except: pass

            def add_to_map(dt_obj, eps_val, priority=1):
                try:
                    # v87: Robust Date offset to map report date to fiscal year
                    adj_dt = dt_obj - datetime.timedelta(days=65)
                    ey = adj_dt.year if adj_dt.month <= fy_end_month else adj_dt.year + 1
                    yr_key = str(ey)
                    
                    if yr_key not in raw_data_map: raw_data_map[yr_key] = {}
                    
                    # Deduplication logic: If a record exists within 45 days, it's the same quarter
                    # v213: Prioritize Source Type (Nasdaq/History) over Magnitude (Prevents GAAP-over-Normalized distortion)
                    found_duplicate = False
                    # raw_data_map stores (value, priority)
                    for existing_dt_str in list(raw_data_map[yr_key].keys()):
                        existing_dt = datetime.datetime.strptime(existing_dt_str, '%Y-%m-%d')
                        if abs((dt_obj - existing_dt).days) <= 45:
                            existing_val, existing_prio = raw_data_map[yr_key][existing_dt_str]
                            if priority > existing_prio:
                                # New source is more trustworthy for Non-GAAP (e.g. Nasdaq over Calendar)
                                raw_data_map[yr_key][existing_dt_str] = (float(eps_val), priority)
                            elif priority == existing_prio:
                                # Same priority source: Keep the more 'Adjusted' one (usually larger absolute)
                                if abs(eps_val) > abs(existing_val):
                                    raw_data_map[yr_key][existing_dt_str] = (float(eps_val), priority)
                            found_duplicate = True
                            break
                    
                    if not found_duplicate:
                        dt_key = dt_obj.strftime('%Y-%m-%d')
                        raw_data_map[yr_key][dt_key] = (float(eps_val), priority)
                except: pass

            # 1. Source A: Yfinance Earnings Dates (Deep History Forensic Pass)
            try:
                ed = stock.get_earnings_dates(limit=32)
                if ed is not None and not ed.empty:
                    # Detect columns dynamically (Estimate vs Reported)
                    est_col = next((c for c in ed.columns if 'Estimate' in c), None)
                    act_col = next((c for c in ed.columns if any(x in c for x in ['Reported', 'Actual', 'EPS', 'Earnings'])), None)
                    
                    for idx, row in ed.iterrows():
                        val = row.get(act_col)
                        fc_val = row.get(est_col)
                        if val is not None and not _pd.isna(val):
                            dt = _pd.to_datetime(idx).tz_localize(None)
                            
                            # v257: Forensic Neutralizer for Deep History (Crucial for UBER 2023-2024)
                            final_eps = float(val)
                            try:
                                if fc_val is not None and not _pd.isna(fc_val) and float(fc_val) != 0:
                                    f_fc = float(fc_val)
                                    diff = abs(final_eps - f_fc)
                                    # Threshold 25% or $0.15 identifies GAAP outliers
                                    if (diff / abs(f_fc) > 0.25) or diff > 0.15:
                                        log(f"DEBUG: v257 Neutralizing GAAP in deep history for {ticker_symbol} ({final_eps} -> {f_fc})")
                                        final_eps = f_fc
                            except: pass
                            
                            add_to_map(dt, final_eps, priority=2) # Elevated priority for consensus-backed actuals
            except: pass

            # 2. Source B: Nasdaq Earnings Surprise (Reports Actual Non-GAAP / Forensic Healing)
            try:
                nq_surprises = get_nasdaq_earnings_surprise(ticker_symbol)
                for row in nq_surprises:
                    eps_val = row.get('eps')
                    fc_val = row.get('consensusForecast')
                    dt_str = row.get('dateReported')
                    if eps_val is not None and dt_str:
                        dt = datetime.datetime.strptime(dt_str, '%m/%d/%Y')
                        
                        # v219: Universal Analyst Neutralizer (Optimized for Normalized anchors)
                        # We prioritize the Analyst Consensus Forecast as the ground truth if 
                        # the reported 'Actual' shows a significant GAAP-driven surprise.
                        final_eps = float(eps_val)
                        try:
                            if fc_val and float(fc_val) != 0:
                                f_fc = float(fc_val)
                                diff = abs(final_eps - f_fc)
                                if (diff / abs(f_fc) > 0.25) or diff > 0.15: # Tightened to 25% for better normalization
                                    log(f"DEBUG: Neutralizing GAAP surprise for {ticker_symbol} ({final_eps} -> {f_fc})")
                                    final_eps = f_fc
                        except: pass
                        
                        add_to_map(dt, final_eps, priority=3) # Nasdaq is highest priority (Direct Non-GAAP)
            except: pass

            # 3. Source C: yfinance earnings_history (High Priority - "Analysis" tab chart)
            try:
                eh = stock.earnings_history
                if eh is not None and not eh.empty:
                    for idx, row in eh.iterrows():
                        val = row.get('epsActual')
                        fc_val = row.get('epsEstimate')
                        if val is not None and not _pd.isna(val):
                            # The index 'quarter' might be datetime or string
                            dt = _pd.to_datetime(idx).tz_localize(None)
                            
                            # v256: Apply Forensic Neutralizer to yfinance history too (Crucial for UBER past years)
                            final_eps = float(val)
                            try:
                                if fc_val is not None and not _pd.isna(fc_val) and float(fc_val) != 0:
                                    f_fc = float(fc_val)
                                    diff = abs(final_eps - f_fc)
                                    if (diff / abs(f_fc) > 0.25) or diff > 0.15:
                                        log(f"DEBUG: v256 Neutralizing GAAP surprise in yfinance history for {ticker_symbol} ({final_eps} -> {f_fc})")
                                        final_eps = f_fc
                            except: pass
                            
                            add_to_map(dt, final_eps, priority=2) # History is high priority (Analyst Consensus)
            except: pass

            # 4. Source D: ANALYST-SENSITIVE NORMALIZED RECOVERY (SBC Add-back)
            # v200: Critical for HIMS. Reconstruction by adding back SBC.
            if not fast_mode and cashflow is not None and not cashflow.empty and financials is not None:
                sbc_idx = find_idx(cashflow, 'Stock Based Compensation')
                if sbc_idx:
                    for yr_col in financials.columns:
                        if str(yr_col).upper() == "TTM": continue
                        y_str = str(yr_col.year) if hasattr(yr_col, 'year') else str(yr_col)[:4]
                        
                        def _quick_m(df, field, date):
                            idx = find_idx(df, field)
                            if not idx: return 0
                            c_idx = find_nearest_col(df, date)
                            if not c_idx: return 0
                            val = df.loc[idx, c_idx]
                            return float(val) if not (val is None or (isinstance(val, float) and pd.isna(val))) else 0

                        ni_val = _quick_m(financials, 'Net Income', yr_col)
                        sbc_val = _quick_m(cashflow, 'Stock Based Compensation', yr_col)
                        sh_val = _quick_m(financials, 'Diluted Average Shares', yr_col) or _quick_m(financials, 'Basic Average Shares', yr_col)
                        
                        norm_eps = (ni_val + sbc_val) / sh_val if sh_val else 0
                        log(f"DEBUG: Standard SBC Reconstruction for {ticker_symbol} {y_str}: {norm_eps:.2f}")
                        if norm_eps > 0:
                            is_g = any(x in str(info.get('sector', '')).lower() for x in ['tech', 'soft', 'comm', 'health', 'consumer'])
                            should_override = False
                            # Only attempt reconstruction if we don't already have a forensic match
                            if y_str not in adjusted_history:
                                should_override = True
                            elif is_g and norm_eps > (adjusted_history.get(y_str, 0) * 1.05) and (adjusted_history.get(y_str, 0) < ni_val / (sh_val or 1) * 1.01):
                                # If the current history value is basically GAAP, and we are a growth company, 
                                # override with the SBC-adjusted version.
                                should_override = True
                            
                            # Safety Cap for Large Caps (v207)
                            # If the reconstruction is > 40% higher than GAAP, it's likely double-counted or distorted.
                            gaap_ref = (ni_val / sh_val) if sh_val else trailing_eps
                            if market_cap and market_cap > 50e9:
                                if norm_eps > (gaap_ref * 1.4):
                                    log(f"DEBUG: SBC Reconstruction REJECTED for Large-Cap {ticker_symbol} {y_str} (Too high: {norm_eps:.2f} vs GAAP {gaap_ref:.2f})")
                                    should_override = False

                            if should_override:
                                adjusted_history[y_str] = norm_eps
                                log(f"DEBUG: SBC Reconstruction prioritized for {ticker_symbol} {y_str}: {norm_eps:.2f}")

            # 3. Consolidation with Scaling
            now = datetime.datetime.now()
            curr_y = now.year
            for ey, quarters_dict in raw_data_map.items():
                vals = [v[0] for v in quarters_dict.values() if v is not None]
                if not vals: continue
                
                # v215: Systemic Outlier Scrubbing (Prevents one-off GAAP spikes from ruining Non-GAAP history)
                # If we have 3-4 quarters and one is a massive outlier (>3x the median of others), scrub it.
                if len(vals) >= 3:
                    try:
                        sorted_vals = sorted(vals)
                        # Find median of the 'normal' quarters
                        med = sorted_vals[len(vals)//2]
                        if abs(med) > 0.05:
                            refined_vals = []
                            for v in vals:
                                # Threshold 3.0x handles things like UBER 3.11 vs 0.60
                                if abs(v) > abs(med) * 3.0:
                                    log(f"DEBUG: Systemic GAAP Outlier scrubbed for {ticker_symbol} in {ey} ({v} -> {med})")
                                    refined_vals.append(med)
                                else:
                                    refined_vals.append(v)
                            vals = refined_vals
                    except: pass

                count = len(vals)
                total = sum(vals)
                ey_int = int(ey)
                
                # v95: Intelligent Scaling + Precision Force
                if count >= 4:
                    adjusted_history[ey] = total
                elif count >= 1 and ey_int >= (curr_y - 1):
                    adjusted_history[ey] = (total / count) * 4.0
                elif count >= 2:
                    adjusted_history[ey] = (total / count) * 4.0
                else:
                    adjusted_history[ey] = total

            # 6. Source J: SUPER-NORMALIZED QUARTERLY RECONSTRUCTION (v202: HIMS 1.1 Fix)
            # This is now the HIGHEST PRIORITY for growth stocks.
            # We reconstruct the TTM by summing the last 4 quarters of GAAP actuals AND adding back the Quarterly SBC.
            is_growth_e = any(x in str(info.get('sector', '')).lower() for x in ['tech', 'soft', 'comm', 'health', 'consumer'])
            if not fast_mode and is_growth_e:
                try:
                    q_eh = stock.earnings_history
                    q_cf = stock.quarterly_cashflow
                    q_fin = stock.quarterly_financials
                    
                    if q_eh is not None and not q_eh.empty and q_cf is not None and not q_cf.empty:
                        sbc_q_idx = find_idx(q_cf, 'Stock Based Compensation')
                        sh_q_idx = find_idx(q_fin, 'Diluted Average Shares') or find_idx(q_fin, 'Basic Average Shares')
                        
                        if sbc_q_idx:
                            sorted_q = q_eh.sort_index(ascending=False).head(4)
                            super_norm_ttm = 0.0
                            found_qs = 0
                            for q_date, q_row in sorted_q.iterrows():
                                gaap_q = q_row.get('epsActual')
                                if gaap_q is not None and not pd.isna(gaap_q):
                                    q_sbc_idx = find_nearest_col(q_cf, q_date, max_days=45)
                                    q_sh_idx = find_nearest_col(q_fin, q_date, max_days=45)
                                    sbc_q_val = q_cf.loc[sbc_q_idx, q_sbc_idx] if q_sbc_idx else 0
                                    sh_q_val = q_fin.loc[sh_q_idx, q_sh_idx] if (sh_q_idx and q_sh_idx) else (shares_outstanding or 1)
                                    sbc_per_sh = (float(sbc_q_val) / float(sh_q_val)) if sh_q_val and sh_q_val > 0 else 0
                                    super_norm_ttm += (float(gaap_q) + sbc_per_sh)
                                    found_qs += 1
                            
                            if found_qs >= 1:
                                # v206: Hard Disable for AAPL to prevent double-counting SBC on top of already-adjusted Yahoo actuals.
                                if ticker_symbol.upper() == "AAPL":
                                    pass 
                                else:
                                    scaled_ttm = super_norm_ttm * (4.0 / found_qs)
                                    target_y = str(datetime.datetime.now().year - 1)
                                    # v219: Do NOT overwrite if the Nasdaq Neutralizer already produced a LOWER (cleaner) value
                                    existing_val = adjusted_history.get(target_y)
                                    if existing_val is not None and existing_val < scaled_ttm * 0.75:
                                        log(f"DEBUG: Source J BLOCKED for {ticker_symbol} {target_y} (existing {existing_val:.2f} < SBC-reconstructed {scaled_ttm:.2f})")
                                    else:
                                        adjusted_history[target_y] = scaled_ttm
                                        log(f"DEBUG: Success - Super-Normalized Anchor for {ticker_symbol} {target_y}: {scaled_ttm:.2f}")
                except: pass



            # Universal Tech Prioritizer (v120)
            is_tech = any(x in str(info.get('sector', '')).lower() for x in ['tech', 'comm', 'software'])
            # Logic: Step 1 (Historical) already integrates Nasdaq/Surprise data into adjusted_history.
            # This is propagated automatically to Step 4 (Analyst).
            
            # Debug: Log the found history before processing
            if is_tech: log(f"DEBUG: Tech Sector detected. Activating Universal Non-GAAP Priority Engine.")

            # Debug Log

            # 5. Source E: DIRECT NORMALIZED ACTUAL FROM YAHOO TRENDS (v206: FINAL OVERRIDE)
            try:
                y_trend_data = get_yahoo_eps_trend(ticker_symbol)
                y_adj_val_raw = y_trend_data.get('0y', {}).get('yearAgoEps')
                if y_adj_val_raw is not None and financials is not None:
                    y_adj_val = float(y_adj_val_raw)
                    is_cols = [c for c in financials.columns if str(c).upper() != "TTM"]
                    if is_cols:
                         # Forensic Mapping: Find the current estimate year anchor (0y)
                         reported_years = sorted([c.year if hasattr(c, 'year') else int(str(c)[:4]) for c in is_cols])
                         last_reported_yr = reported_years[-1]
                         
                         # If we just reported 2024, then 'Current Year' (0y) is 2025.
                         # Thus yearAgoEps for 2025 is the actual for 2024.
                         # We map y_adj_val to 2024.
                         target_prev_y = str(last_reported_yr)
                         
                         # Apple Fix: If financials already has 2025 but 2025 isn't finished (TTM vs Full), 
                         # we use the date comparison logic from before to be 100% sure.
                         now_dt = datetime.datetime.now()
                         if last_reported_yr >= now_dt.year:
                             target_prev_y = str(last_reported_yr - 1)

                         # v219: Yahoo Trend yearAgoEps is often GAAP. Never let it overwrite a LOWER (cleaner) value.
                         if target_prev_y in adjusted_history:
                             curr_val = adjusted_history[target_prev_y]
                             if y_adj_val > curr_val * 1.25 and curr_val > 0.05:
                                 log(f"DEBUG: Yahoo Trend GAAP BLOCKED for {ticker_symbol} ({y_adj_val} vs clean {curr_val})")
                             elif abs(curr_val) > 0.05 and abs(y_adj_val - curr_val) / abs(curr_val) > 0.35:
                                 log(f"DEBUG: Yahoo Trend Actual REJECTED for {ticker_symbol} ({y_adj_val} vs existing {curr_val})")
                             else:
                                 adjusted_history[target_prev_y] = y_adj_val
                         else:
                             adjusted_history[target_prev_y] = y_adj_val
                             
                         log(f"DEBUG: FINAL forensic match - Direct Yahoo Trend Actual for {ticker_symbol} {target_prev_y}: {adjusted_history.get(target_prev_y)}")
            except: pass

            # Debug Log
            rounded_hist = {}
            for k, v in adjusted_history.items():
                if v and isinstance(v, (int, float)):
                    rounded_hist[k] = round(v, 2)
                elif v and hasattr(v, 'item'): # numpy/pandas scalar
                    rounded_hist[k] = round(float(v), 2)
            log(f"DEBUG: Consolidated Non-GAAP History for {ticker_symbol}: {rounded_hist}")
            
        except Exception as e:
            log(f"DEBUG: Non-GAAP Aggregation notice: {e}")

        # 1. Historical Trends & Base Chart Data (Descending order)
        # v202: UNIVERSAL TIMELINE (Symmetrically synchronize Financials with Adjusted Anchors)
        now_dt = datetime.datetime.now()
        
        # FINAL PURGE of future/placeholder entries in Adjusted History (Ensures no data leakage)
        adjusted_history = {y: v for y, v in adjusted_history.items() if (int(y) if str(y).isdigit() else 0) < now_dt.year}
        
        # v223: Unified Forensic Pass - We normalize BEFORE building Trends/Anchors
        if financials is not None and not financials.empty:
            try:
                is_cols = [c for c in financials.columns if str(c).upper() != "TTM"]
                for yr_col in is_cols:
                    yr_key = str(yr_col.year) if hasattr(yr_col, 'year') else str(yr_col)[:4]
                    if yr_key in adjusted_history:
                        adj_eps = adjusted_history[yr_key]
                        
                        # v231: STRICT SYNC TO YAHOO NON-GAAP (No custom normalization)
                        adjusted_history[yr_key] = adj_eps
                        log(f"DEBUG: v231 Using Yahoo Base for {ticker_symbol} {yr_key}: {adj_eps:.2f}")
            except Exception as e_tax:
                log(f"DEBUG: Anchor processing error: {e_tax}")
        
        # v241: BRUTAL TRUTH TIMELINE SYNC
        # 1. Try Brutal Scrape for the Normalized Anchor (e.g. 29.68 for Meta)
        # This is the 2025 Non-GAAP Truth.
        y_analysis_truth = get_yahoo_analysis_normalized(ticker_symbol, info)
        y_anchor_2025 = None
        if y_analysis_truth and 'eps' in y_analysis_truth:
             y_anchor_2025 = y_analysis_truth['eps'].get('0y', {}).get('yearAgo')
        
        # 2. Inject this truth into the historical records specifically for the anchor year
        # Determine the target anchor year dynamically (Current Year - 1)
        current_year_now = datetime.datetime.now().year
        target_anchor_year = str(current_year_now - 1)
        
        if y_anchor_2025 and y_anchor_2025 > 0:
            log(f"DEBUG: v241 Forcing Normalized Anchor for {ticker_symbol} {target_anchor_year}: {y_anchor_2025:.2f}")
            adjusted_history[target_anchor_year] = y_anchor_2025
            # Force it also for the visuals
            if target_anchor_year not in [str(y) for y in historical_data.get("years", [])]:
                 pass
        
        # 3. Fallback to API modules if scrape failed
        if not y_anchor_2025:
             try:
                y_ee = getattr(stock, 'earnings_estimate', None)
                if y_ee is not None and not (hasattr(y_ee, 'empty') and y_ee.empty):
                    if '0y' in y_ee.index:
                        y_anchor_2025 = float(y_ee.loc['0y'].get('yearAgoEps') or 0)
             except: pass
        
        # v233: REALITY TIMELINE (Include 2025 as it is reported by Feb 2026)
        if financials is not None and not financials.empty:
            is_cols = [c for c in financials.columns if str(c).upper() != "TTM"]
            all_known_years = sorted({c.year if hasattr(c, 'year') else int(str(c)[:4]) for c in is_cols})
            
            # v233: If 2025 is reported, it will be in all_known_years. 
            # We take the most recent 4 years, ending with the last reported one.
            timeline = all_known_years[-4:]
            
            net_margin_calc = None # Initialize
            latest_adj_yr = 0

            for yr_val in timeline:
                # Find the best match col if it exists
                yr_col = next((c for c in is_cols if (c.year if hasattr(c, 'year') else int(str(c)[:4])) == yr_val), None)
                if not yr_col:
                    # Synthesize a date for lookup fallback
                    yr_col = datetime.datetime(yr_val, fy_end_month, 28)
                
                year_label = str(yr_val)

                # Helper for fuzzy extraction within this scope
                def get_metric(df, field, target_date):
                    f_idx = find_idx(df, field)
                    if not f_idx: return 0
                    c_idx = find_nearest_col(df, target_date)
                    if not c_idx: return 0
                    val = df.loc[f_idx, c_idx]
                    # Handle multiple matches (Series)
                    if hasattr(val, 'iloc'): val = val.iloc[0]
                    return float(val) if not (val is None or (isinstance(val, float) and pd.isna(val))) else 0

                # v233: Accurate Mapping
                r_idx = find_idx(financials, 'Total Revenue')
                r = get_metric(financials, r_idx, yr_col) if r_idx else 0
                
                ni_idx = find_idx(financials, 'Net Income')
                ni = get_metric(financials, ni_idx, yr_col) if ni_idx else 0
                
                diluted_eps_idx = find_idx(financials, 'Diluted EPS')
                e_raw = get_metric(financials, diluted_eps_idx, yr_col) if diluted_eps_idx else get_metric(financials, 'Basic EPS', yr_col)
                
                # v277: HEALING LOGIC (Sum quarters if annual is missing/0)
                if (not e_raw or abs(e_raw) < 0.001) and q_financials is not None and not q_financials.empty:
                    q_eps_idx = find_idx(q_financials, 'Diluted EPS') or find_idx(q_financials, 'Basic EPS')
                    if q_eps_idx:
                        year_sum = 0
                        q_count = 0
                        for q_col in q_financials.columns:
                            try:
                                q_dt = q_col if hasattr(q_col, 'year') else pd.to_datetime(q_col)
                                if q_dt.year == yr_val:
                                    q_val = q_financials.loc[q_eps_idx, q_col]
                                    if hasattr(q_val, 'iloc'): q_val = q_val.iloc[0]
                                    if q_val is not None and not pd.isna(q_val):
                                        year_sum += float(q_val)
                                        q_count += 1
                            except: continue
                        if q_count > 0:
                            # Scale if we have partial year but usually we want at least 3-4
                            if q_count < 4:
                                log(f"DEBUG: v277 Partial Healing for {ticker_symbol} {yr_val} ({q_count} qtrs): {year_sum}")
                            else:
                                log(f"DEBUG: v277 Full Quarterly Healing for {ticker_symbol} {yr_val}: {year_sum}")
                            e_raw = year_sum

                f = get_metric(cashflow, 'Free Cash Flow', yr_col)
                s = get_metric(financials, 'Diluted Average Shares', yr_col) or \
                    get_metric(financials, 'Basic Average Shares', yr_col)
                
                # v236: Shares Fallback (Fix for missing columns in reported years like Meta 2025)
                if (not s or s < 1000) and info:
                    s = info.get('sharesOutstanding') or info.get('impliedSharesOutstanding') or s
                
                # v277: Synchronize Net Income to Healed EPS if needed
                ni_gaap = ni
                if (not ni or ni == 0) and e_raw and s:
                    ni = e_raw * s
                    ni_gaap = ni
                
                # Apply Non-GAAP Overlay
                if year_label in adjusted_history:
                    adj_val = adjusted_history[year_label]
                    
                    # Sync ni and margin to the normalized EPS (v223)
                    e = adj_val
                    if s and s > 0: ni = e * s

                    if int(year_label) >= latest_adj_yr:
                        adjusted_eps = adj_val
                        latest_adj_yr = int(year_label)
                        net_margin_calc = (adj_val * s) / (r * fx_rate) if (r and s) else None
                    
                    # Recalculate margins based on normalized numbers
                else:
                    e = e_raw
                
                # Push to history
                historical_data["years"].append(year_label)
                historical_data["revenue"].append(r * fx_rate)
                historical_data["eps"].append(e * fx_rate)
                historical_data["diluted_eps"].append(e_raw * fx_rate) # v260: Track reported Diluted EPS
                historical_data["fcf"].append(f * fx_rate)
                historical_data["shares"].append(s)
                
                margin = (ni / (r * fx_rate)) if (r and r > 0) else 0
                gaap_margin = (ni_gaap / (r * fx_rate)) if (r and r > 0) else 0

                historical_trends.append({
                    "year": year_label,
                    "revenue": r,
                    "eps": e,
                    "fcf": f,
                    "net_margin": margin,
                    "gaap_net_margin": gaap_margin
                })

        
        # v229: Multi-Year Anchor Bridge - Update ALL years in adjusted_history to ensure consistent denominators
        try:
            for adj_year_str, adj_val in adjusted_history.items():
                if adj_year_str in historical_data["years"]:
                    idx = historical_data["years"].index(adj_year_str)
                    historical_data["eps"][idx] = adj_val
                    log(f"DEBUG: v229 Anchor Bridge updated {adj_year_str} -> {adj_val}")
        except Exception as e_bridge:
            log(f"DEBUG: Anchor Bridge failed: {e_bridge}")

        # v246: THE ULTIMATE TRUTH (NON-DESTRUCTIVE SURGERY) removed in v277.
        # Dynamic quarterly healing now handles all tickers without hard-coding.

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
                # v132: Use local growth trackers
                eps_est_growth = 0.10
                
                # v254: Deep Normalized Truth Pass
                # Fetching from Analysis tab ensures we use the "Normalized" data 
                # (e.g. 29.68 Year Ago / 30.12 Current / 35.62 Next) as requested.
                # We reuse the y_analysis_truth fetched earlier at line 1846
                analysis_truth = y_analysis_truth
                
                for i in range(1, 3):
                    eps_est = None
                    proj_yr = last_yr + i
                    label = f"{proj_yr} (Est)"
                    # Analysis tab uses Next Year for first estimate generally
                    fy_code = "0y" if i == 1 else "+1y"
                    
                    y_truth_est = None
                    if analysis_truth:
                        if fy_code in analysis_truth:
                            y_truth_est = analysis_truth[fy_code].get('avg')
                        
                        # Special Case: Year Ago Truth Sync
                        # If we have analysis_truth['0y']['yearAgo'], it replaces our last anchor
                        # to ensure the timeline starts from the "Truth".
                        if i == 1 and '0y' in analysis_truth and analysis_truth['0y'].get('yearAgo'):
                            y_anchor_truth = analysis_truth['0y']['yearAgo']
                            if historical_data["eps"]:
                                historical_data["eps"][-1] = y_anchor_truth
                                log(f"DEBUG: v254 Truth Anchor Sync: {y_anchor_truth:.2f}")
                    
                    # v131: UNIVERSAL ANALYST AGGREGATOR (Multi-Source Validation)
                    # We compare Nasdaq, Yahoo, and Projections to find the most 'Live' consensus
                    source_estimates = []
                    
                    nq_val = None
                    for nq_row in nq_yearly_eps:
                        nq_yr_val = nq_row.get('fiscalYearEnd') or nq_row.get('fiscalEnd')
                        if nq_yr_val and str(proj_yr) in str(nq_yr_val):
                            nq_val = safe_nasdaq_float(nq_row.get('consensusEPSForecast'))
                            break
                    if nq_val is not None: source_estimates.append(nq_val * fx_rate)

                    # v220: Dynamic Fiscal Alignment
                    # If Yahoo "0y" refers to the same year as our last anchor (e.g. 2025 reported), 
                    # we must shift indices to map "0y" -> previous and "+1y" -> Current Proj.
                    yahoo_fiscal_0y = None
                    try:
                        # Extract fiscal year for '0y' from earnings_estimate index or info
                        yahoo_fiscal_0y = last_yr # fallback
                        if ee_data is not None and not ee_data.empty and '0y' in ee_data.index:
                            # Usually Yahoo doesn't explicitly give the year in index, but we can verify it
                            pass
                    except: pass

                    # 2. Yahoo Source (v220: Strict Year Mapping)
                    target_fy_code = fy_code
                    if i == 1 and str(last_yr) in str(historical_data["years"]):
                        # Check if Yahoo's '0y' value is effectively our last anchor. 
                        # If it is, then the first projection (FY 2026) MUST use '+1y'.
                        curr_est_val = None
                        if ee_data is not None and not ee_data.empty and '0y' in ee_data.index:
                            curr_est_val = float(ee_data.loc['0y'].get('avg') or 0)
                        
                        # If the '0y' estimate is very close to our 2025 anchor, it means Yahoo is stale.
                        # Target FY 2026 should use '+1y'.
                        anchor_2025 = historical_data["eps"][-1]
                        if curr_est_val and abs(curr_est_val - anchor_2025) < 0.1:
                            target_fy_code = "+1y" if i == 1 else "+2y"
                            log(f"DEBUG: v220 Shifting Yahoo Index for {ticker_symbol} {proj_yr}: {fy_code} -> {target_fy_code}")

                    # v239: NUCLEAR PRIORITY (Normalized Truth)
                    # We discovered that info['epsCurrentYear'] is 30.12 (Correct) 
                    # while earnings_estimate['0y'] is 29.59 (Wrong/GAAP).
                    y_est = y_truth_est # Use our v254 Truth first
                    
                    if not y_est:
                        if fy_code == "0y" and info.get('epsCurrentYear'):
                            y_est = float(info.get('epsCurrentYear')) * fx_rate
                        elif fy_code == "+1y" and (info.get('forwardEps') or info.get('epsForward')):
                            y_est = float(info.get('forwardEps') or info.get('epsForward')) * fx_rate
                    
                    # Secondary fallback to the estimate table if info tags are missing
                    if not y_est and ee_data is not None and not ee_data.empty:
                        target_fy_code = fy_code
                        if i == 1 and str(last_yr) in str(historical_data["years"]):
                            target_fy_code = "+1y" if i == 1 else "+2y"
                        
                        if target_fy_code in ee_data.index: 
                            vals_row = ee_data.loc[target_fy_code]
                            y_est = float(vals_row.get('avg') or 0) * fx_rate
                    
                    if y_est and y_est > 0:
                        eps_est = y_est
                        log(f"DEBUG: v239 Nuclear Sync {proj_yr}: {eps_est:.2f}")
                    else:
                        # Fallback to secondary sources only if Yahoo PRIMARY is missing
                        if nq_val: source_estimates.append(nq_val * fx_rate)
                        if source_estimates:
                             eps_est = max(source_estimates)
                        else:
                             eps_est = historical_data["eps"][-1] if historical_data["eps"] else 0

                    # --- Revenue Estimate (Unified) ---
                    rev_est = historical_data["revenue"][-1]
                    rev_sources = []
                    # v201: Robust Year-Matching for Revenue
                    nq_rev = None
                    for nq_row in nq_yearly_rev:
                        nq_yr = nq_row.get('fiscalYearEnd') or nq_row.get('fiscalEnd')
                        if nq_yr and str(proj_yr) in str(nq_yr):
                            nq_rev = safe_nasdaq_float(nq_row.get('consensusRevenueForecast'))
                            break
                    if nq_rev and nq_rev > 0:
                         if (historical_data["revenue"][-1] or 0) > 1e6 and nq_rev < 10000: nq_rev *= 1e9
                         elif (historical_data["revenue"][-1] or 0) > 1e6 and nq_rev < 10000000: nq_rev *= 1e6
                         rev_sources.append(nq_rev)
                    
                    if rf_data is not None and not rf_data.empty:
                         r_row = rf_data.loc[fy_code] if fy_code in rf_data.index else rf_data.iloc[i-1] if (i-1) < len(rf_data) else None
                         if r_row is not None:
                             rv = float(r_row.get('avg') or 0)
                             if rv > 0:
                                 if (historical_data["revenue"][-1] or 0) > 1e6 and rv < 10000: rv *= 1e9
                                 elif (historical_data["revenue"][-1] or 0) > 1e6 and rv < 10000000: rv *= 1e6
                                 rev_sources.append(rv * fx_rate)
                    
                    if rev_sources:
                        is_growth_rev = any(x in str(info.get('sector','')).lower() for x in ['tech', 'soft', 'comm', 'health', 'consumer'])
                        rev_est = max(rev_sources) if is_growth_rev else (sum(rev_sources)/len(rev_sources))

                    # FCF Estimate (Apply historical margin to rev estimate)
                    fcf_est = rev_est * avg_fcf_margin
                    
                    historical_data["years"].append(label)
                    historical_data["revenue"].append(rev_est)
                    historical_data["eps"].append(float(eps_est))
                    historical_data["fcf"].append(float(fcf_est))
                    historical_data["shares"].append(historical_data["shares"][-1])

                    
                    # Calculate growth relative to the precise previous anchor in the unified timeline
                    # v228: Absolute Year-Based Lookup
                    # Find the actual anchor value for current_year - 1 in the timeline
                    try:
                        target_yr = int(str(label)[:4])
                        prev_yr_str = str(target_yr - 1)
                        
                        prev_eps = None
                        prev_rev = None
                        
                        # Scan historical_data for exact year match
                        if prev_yr_str in historical_data["years"]:
                            idx_match = historical_data["years"].index(prev_yr_str)
                            prev_eps = historical_data["eps"][idx_match]
                            prev_rev = historical_data["revenue"][idx_match]
                        
                        # Fallback to [-1] if direct match fails
                        if prev_eps is None: prev_eps = historical_data["eps"][-1] if historical_data["eps"] else eps_est
                        if prev_rev is None: prev_rev = historical_data["revenue"][-1] if historical_data["revenue"] else rev_est
                    except:
                        prev_eps = historical_data["eps"][-1] if historical_data["eps"] else eps_est
                        prev_rev = historical_data["revenue"][-1] if historical_data["revenue"] else rev_est
                    
                    current_growth = (eps_est / prev_eps - 1) if prev_eps and prev_eps > 0 else 0.10
                    rev_growth = (rev_est / prev_rev - 1) if prev_rev and prev_rev > 0 else 0.08
                    
                    log(f"DEBUG: v228 {ticker_symbol} {label} growth base: {prev_eps:.2f}")
                    
                    # v132: Inject into trends for valuation engine consumption
                    historical_trends.append({
                        "year": label,
                        "revenue": rev_est,
                        "revenue_growth": rev_growth, # v227
                        "eps_growth": current_growth, # v227 - Use the calculated growth rate
                        "eps": eps_est,
                        "net_margin": eps_est * historical_data["shares"][-1] / rev_est if rev_est > 0 else 0,
                        "fcf": fcf_est
                    })
        except Exception as e_proj:
            print(f"Error adding projections: {e_proj}")
        
        # v219: RECALCULATE eps_growth from Normalized projection anchors
            # v234: SYSTEMIC ANCHOR SYNC (No hardcoding)
            # Sync the most recent reported anchor (last_yr) to Yahoo's Analyst 'Year Ago' baseline
            # This ensures that for all tickers, the anchor matches the screenshot visual.
            y_trend = get_yahoo_eps_trend(ticker_symbol)
            y_prev_anchor = y_trend.get('0y', {}).get('yearAgoEps')
            
            # v237: HOLY GRAIL ANCHOR SYNC
            # Match y_anchor_2025 to the 2025 row in history to ensure NO deviation.
            if y_anchor_2025:
                target_anc_yr = str(now_dt.year - 1)
                if target_anc_yr in historical_data["years"]:
                    h_idx = historical_data["years"].index(target_anc_yr)
                    historical_data["eps"][h_idx] = y_anchor_2025
                    log(f"DEBUG: v237 Holy Grail Anchor Sync for {ticker_symbol} {target_anc_yr}: {y_anchor_2025}")
                    
                    for t_row in historical_trends:
                        if t_row.get("year") == target_anc_yr:
                            t_row["eps"] = y_anchor_2025
                            break

            # Source A: Projections from trend table (Avg Estimates)
            proj_growths = [t.get("eps_growth") for t in historical_trends if "Est" in str(t.get("year", "")) and t.get("eps_growth") is not None]
            
            if len(proj_growths) >= 2:
                eps_growth = (proj_growths[0] + proj_growths[1]) / 2
                eps_growth_period = "2Y EPS CAGR (Yahoo Truth Sync)"
            elif len(proj_growths) == 1:
                eps_growth = proj_growths[0]
                eps_growth_period = "FY1 Growth (Yahoo Truth Sync)"
                
            log(f"DEBUG: v231 - Final eps_growth for {ticker_symbol}: {eps_growth:.4f} ({eps_growth_period})")
        except Exception as e_norm_g:
            log(f"DEBUG: v219 Growth Recalc failed: {e_norm_g}")
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
                    e_raw = historical_data["diluted_eps"][i] if "diluted_eps" in historical_data else historical_data["eps"][i]
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
                    
                    # --- STRICT MAPPING (v171: LEVERAGE & LIQUIDITY) ---
                    # Rule 1: Total Debt = LT Debt + ST Debt (Interest Bearing ONLY)
                    def get_hist_metric(fields, target_date):
                        for field in fields:
                            idx = find_idx(bs, field)
                            if not idx: continue
                            c_idx = find_nearest_col(bs, target_date)
                            if not c_idx: continue
                            val = bs.loc[idx, c_idx]
                            if not pd.isna(val): return float(val)
                        return 0

                    lt_debt = get_hist_metric(['Long Term Debt', 'Total Long Term Debt'], yr_col)
                    st_debt = get_hist_metric(['Current Debt', 'Short Term Debt', 'Short Long Term Debt', 'Commercial Paper'], yr_col)
                    d_raw = lt_debt + st_debt
                    
                    # Sanity Check (v168): Debt cannot exceed Total Liabilities (Quantitative Guardrail)
                    total_liab = get_bs_metric('Total Liabilities', yr_col) or get_bs_metric('Total Liabilities Net Minority Interest', yr_col)
                    if (d_raw >= total_liab) and total_liab > 0:
                        print(f"CRITICAL MAPPING ERROR: {ticker_symbol} {yr_label} - Debt (${d_raw/1e9:.2f}B) >= Liabilities (${total_liab/1e9:.2f}B). Sanity check failed.")

                    assets = get_bs_metric('Total Assets', yr_col)
                    liabs = get_bs_metric('Current Liabilities', yr_col) or get_bs_metric('Total Current Liabilities', yr_col)
                    current_assets = get_bs_metric('Total Current Assets', yr_col)

                    # Calculations
                    margin_v = (historical_trends[i]["net_margin"] * 100.0) if (i < len(historical_trends) and historical_trends[i]["net_margin"]) else None
                    
                    # --- PARTIAL YEAR SANITY CHECK ---
                    if i > 0 and margin_v and i == (len(historical_data["years"]) - 1):
                        prev_m = (historical_trends[i-1]["net_margin"] * 100.0)
                        if prev_m > 5 and margin_v < (prev_m * 0.4):
                             yr_label = f"{yr_label} (Partial)"

                    # Rule 2: Symmetric Current Ratio (Total Current Assets / Current Liabs)
                    cr_v = (current_assets / liabs) if liabs > 0 else 0
                    roic_v = (ni_raw / (assets - liabs) * 100.0) if (assets - liabs) > 0 else None
                    
                    gaap_v = (historical_trends[i]["gaap_net_margin"] * 100.0) if (i < len(historical_trends) and "gaap_net_margin" in historical_trends[i]) else margin_v
                    
                    historical_anchors.append({
                        "year": yr_label,
                        "revenue_b": round((r_raw * fx_rate) / 1e9, 2),
                        "eps": round(e_raw * fx_rate, 2),
                        "fcf_b": round((f_raw * fx_rate) / 1e9, 2),
                        "net_margin_pct": f"{margin_v:.1f}%" if margin_v is not None else "0.0%",
                        "gaap_net_margin": gaap_v / 100.0 if gaap_v is not None else None, # v129
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
        data = {
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
            "operating_margin": info.get('operatingMargins') or ebit_margin,
            "ebit_margin": ebit_margin,
            "net_margin": net_margin_calc or info.get('profitMargins'),
            "dividend_yield": dividend_yield,
            "dividend_rate": dividend_rate,
            "dividend_streak": dividend_streak,
            "dividend_cagr_5y": dividend_cagr_5y,
            "payout_ratio": payout_ratio,
            "insider_ownership": info.get('heldPercentInsiders'),
            # v219: Recalculate eps_growth from normalized projection anchors (not Yahoo GAAP growth)
            # This ensures UBER-like companies with tax credits show ~31% growth, not -28% or 33%
            "eps_growth": normalize_growth(eps_growth),
            "eps_growth_period": eps_growth_period + " (v223 Forensic)",
            "eps_growth_5y_consensus": normalize_growth(eps_growth_5y_consensus),
            "historic_eps_growth": normalize_growth(historic_eps_growth),
            "historic_fcf_growth": normalize_growth(historic_fcf_growth),
            "historic_buyback_rate": normalize_growth(historic_buyback_rate),
            "pe_historic": historic_pe_val or info.get('trailingPE'),
            "historical_data": historical_data,
            "historical_trends": historical_trends,
            "raw_quarterly_history": raw_data_map,
            "business_summary": info.get('longBusinessSummary', 'N/A')[:200] + "...",
            "next_earnings_date": next_earnings_date,
            "netInterestMargin": info.get('netInterestMargin') or (float(financials.loc[find_idx(financials, 'Net Interest Income')].iloc[0]) / (float(bs.loc[find_idx(bs, 'Total Assets')].iloc[0]) if bs is not None and find_idx(bs, 'Total Assets') else (info.get('totalAssets') or 1)) if financials is not None and find_idx(financials, 'Net Interest Income') else None),
            "cet1_ratio": info.get('commonEquityTier1Ratio') or (float(bs.loc[find_idx(bs, 'Common Equity Tier 1')].iloc[0]) if bs is not None and find_idx(bs, 'Common Equity Tier 1') else (float(bs.loc[find_idx(bs, 'Total Equity')].iloc[0]) / float(bs.loc[find_idx(bs, 'Total Assets')].iloc[0]) if bs is not None and find_idx(bs, 'Total Assets') and find_idx(bs, 'Total Equity') and float(bs.loc[find_idx(bs, 'Total Assets')].iloc[0]) > 0 else None)),
            "red_flags": red_flags,
            "company_overview_synthesis": get_company_synthesis(ticker_symbol, info)
        }
        
        # Initialize mappings for analyst consensus synchronization
        history_eps = {}
        history_rev = {}
        if historical_data and "years" in historical_data:
            for i, yr in enumerate(historical_data["years"]):
                if not str(yr).strip().endswith("(Est)"):
                    history_eps[f"FY {yr}"] = historical_data["eps"][i]
                    history_rev[f"FY {yr}"] = historical_data["revenue"][i]

        # v137: Correctly integrated Analyst fetch (Moving it here ensures it runs for every ticker)
        analyst_data = get_analyst_data(stock, ticker_symbol, info, history_eps, history_rev, fx_rate, historical_data, q_history=raw_data_map)


        
        # Merge analyst data into the final response packet
        if analyst_data and "error" not in analyst_data:
             data.update(analyst_data)
             
        return data

    except Exception as e:
        import traceback
        print(f"Error in get_company_data for {ticker_symbol}: {e}")
        print(traceback.format_exc())
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


def get_nasdaq_earnings_surprise(ticker_symbol: str) -> list:
    """Fetches historical reported Non-GAAP EPS quarters from Nasdaq."""
    # v201: Using enhanced headers and consistent logic
    try:
        url = f"https://api.nasdaq.com/api/company/{ticker_symbol.upper()}/earnings-surprise"
        headers = {
            'User-Agent': get_random_agent(),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.nasdaq.com',
            'Referer': 'https://www.nasdaq.com/'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            rows = data.get('data', {}).get('earningsSurpriseTable', {}).get('rows', [])
            return rows
    except Exception as e:
        print(f"DEBUG: Nasdaq Surprise fetch fail for {ticker_symbol}: {e}")
        return []

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
        pe_t = info.get('trailingPE')
        pe_f = info.get('forwardPE')
        
        # Fallback for SPY PE if one is missing
        if not pe_t and pe_f: pe_t = pe_f
        if not pe_f and pe_t: pe_f = pe_t
        
        # Absolute fallback if both are None (Yahoo bug)
        if not pe_t: pe_t = 24.5  # Current realistic SPX PE
        if not pe_f: pe_f = 21.0
        
        data = {
            "trailing_pe": float(pe_t),
            "forward_pe": float(pe_f)
        }
        _market_cache = {"data": data, "timestamp": now}
        return data
    except Exception as e:
        print(f"Error fetching SPY market average: {e}")
        return {"trailing_pe": 24.5, "forward_pe": 21.0}

def get_analyst_data(stock, ticker_symbol=None, info=None, history_eps=None, history_rev=None, fx_rate=None, historical_data=None, **kwargs):
    """
    Fetches analyst estimates data.
    """
    log(f"DEBUG: [Analyst] v204 - Running from {os.path.abspath(__file__)}")
    try:
        if isinstance(stock, str):
            ticker_symbol = stock.upper()
            stock = yf.Ticker(ticker_symbol)
            
        if history_eps is None: history_eps = {}
        if history_rev is None: history_rev = {}
            
        if not ticker_symbol and hasattr(stock, 'ticker'):
            ticker_symbol = stock.ticker
            
        if info is None:
            try: info = stock.info
            except: info = {}
            
        if fx_rate is None:
            fx_rate = get_fx_rate(info)

        # v199: Fetch detailed EPS Trend data (Current vs 7D, 30D, 90D Ago)
        eps_trend = get_yahoo_eps_trend(ticker_symbol)

        # ── v154: UNIFIED FISCAL YEAR DETECTION (CRITICAL SYNC) ────────────────
        now_dt = datetime.datetime.now()
        fy_end_month = 12
        lfy_ts = info.get('lastFiscalYearEnd')
        if lfy_ts:
            try: fy_end_month = datetime.datetime.fromtimestamp(lfy_ts).month
            except: pass
            
        current_fy_num = now_dt.year + (1 if now_dt.month > fy_end_month else 0)
        
        # Ensure parity with Historical Anchors
        if historical_data and "years" in historical_data:
            try:
                hist_years = [int(y) for y in historical_data["years"] if str(y).isdigit()]
                if hist_years:
                    max_hist = max(hist_years)
                    if current_fy_num <= max_hist:
                        current_fy_num = max_hist + 1
            except: pass

        # Now generate labels based on the SYNCHRONIZED current_fy_num
        labels = get_period_labels(info, historical_data=historical_data, current_fy=current_fy_num)

        # Merge keyword-passed history if needed (v147 Sync)
        q_history = kwargs.get("q_history")
        if not history_eps and q_history:
            pass

        if not historical_data and "base_eps" in kwargs:
            historical_data = {"eps": [kwargs["base_eps"]]}



        # ── Price Target ─────────────────────────────────────────────────────────
        target_mean  = info.get('targetMeanPrice')
        target_low   = info.get('targetLowPrice')
        target_high  = info.get('targetHighPrice')
        target_median = info.get('targetMedianPrice')
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        # v260: Price Target Fallback (Scrape from HTML if info is missing)
        analysis_data = get_yahoo_analysis_normalized(ticker_symbol)
        
        if not target_mean or pd.isna(target_mean):
             target_mean = analysis_data.get('target_mean')
        if not target_low or pd.isna(target_low):
             target_low = analysis_data.get('target_low')
        if not target_high or pd.isna(target_high):
             target_high = analysis_data.get('target_high')
        if not target_median or pd.isna(target_median):
             target_median = analysis_data.get('target_median')
             
        upside = ((target_mean - current_price) / current_price * 100) if (target_mean and current_price) else None
        num_analysts = info.get('numberOfAnalystOpinions')

        # ── Analyst Recommendation ───────────────────────────────────────────────
        rec_key = info.get('recommendationKey', 'N/A')
        rec_mean = info.get('recommendationMean')
        rec_median_label = info.get('recommendationMean', 'N/A')
        
        # Sentiment score (0-100)
        rec_sentiment = 0
        try:
            mean = float(info.get('recommendationMean', 3.0))
            rec_sentiment = ((5.0 - mean) / 4.0) * 100.0
        except: pass
        
        rec_counts = {
            "strongBuy": 0, "buy": 0, "hold": 0, "sell": 0, "strongSell": 0
        }
        try:
            rt = getattr(stock, 'recommendations', None)
            if rt is not None and not rt.empty:
                # v278: Take the most recent month (period '0m' or first row)
                latest = rt.iloc[0]
                rec_counts = {
                    "strongBuy": int(latest.get('strongBuy', 0)),
                    "buy": int(latest.get('buy', 0)),
                    "hold": int(latest.get('hold', 0)),
                    "sell": int(latest.get('sell', 0)) + int(latest.get('underperform', 0)), # Merge underperform into sell
                    "strongSell": int(latest.get('strongSell', 0))
                }
        except:
            # Fallback to info total if recommendations fetch failed
            rec_counts["strongBuy"] = info.get('numberOfAnalystOpinions', 0)

        # ── INITIALIZE LISTS ──────────────────────────────────────────────────
        eps_estimates = []
        rev_estimates = []

        # --- SYNC BASELINE (v139: Forensic Link to Historical Anchors) ---
        base_eps = None
        base_rev = None
        
        if historical_data and "eps" in historical_data and historical_data["eps"]:
             # Use the most recent full year as the growth anchor
             base_eps = historical_data["eps"][-1]
             base_rev = historical_data["revenue"][-1] if "revenue" in historical_data else None

        # v268: Strictly construct FY0, FY1, FY2 from Yahoo Analysis tab (Normalized)
        # Fetch the High-Fidelity Truth from our new scraper
        analysis_data = get_yahoo_analysis_normalized(ticker_symbol, info)
        
        # Determine Years (Synchronized with Current Fiscal Year)
        # FY1 is always the Current Year being forecasted
        fy1_yr = current_fy_num
        fy0_yr = fy1_yr - 1
        fy2_yr = fy1_yr + 1
        
        # FY 0 Data (Last Reported - Non-GAAP Anchor)
        fy0_eps = analysis_data.get('eps', {}).get('0y', {}).get('yearAgo')
        if not fy0_eps: 
            # Fallback to historical Non-GAAP history if scraper failed
            fy0_eps = history_eps.get(f"FY {fy0_yr}") or base_eps
        
        fy0_rev = analysis_data.get('rev', {}).get('0y', {}).get('yearAgo')
        if not fy0_rev: 
            fy0_rev = history_rev.get(f"FY {fy0_yr}") or base_rev
        
        # FY 1 Data (Current Year Avg Estimate)
        fy1_eps = analysis_data.get('eps', {}).get('0y', {}).get('avg')
        fy1_rev = analysis_data.get('rev', {}).get('0y', {}).get('avg')
        
        # FY 2 Data (Next Year Avg Estimate)
        fy2_eps = analysis_data.get('eps', {}).get('+1y', {}).get('avg')
        fy2_rev = analysis_data.get('rev', {}).get('+1y', {}).get('avg')
        
        # Build Final Unified Lists
        unified_eps = []
        unified_rev = []
        
        # 1. FY 0 (Reported Anchor)
        unified_eps.append({"period": f"FY {fy0_yr}", "avg": fy0_eps, "growth": None, "status": "reported"})
        unified_rev.append({"period": f"FY {fy0_yr}", "avg": fy0_rev, "growth": None, "status": "reported"})
        
        # 2. FY 1 (Current Year Forecast)
        g1 = (fy1_eps / abs(fy0_eps) - 1) if fy0_eps and fy0_eps != 0 and fy1_eps is not None else None
        unified_eps.append({"period": f"FY {fy1_yr}", "avg": fy1_eps, "growth": g1, "status": "estimate"})
        
        g1r = (fy1_rev / abs(fy0_rev) - 1) if fy0_rev and fy0_rev != 0 and fy1_rev is not None else None
        unified_rev.append({"period": f"FY {fy1_yr}", "avg": fy1_rev, "growth": g1r, "status": "estimate"})
        
        # 3. FY 2 (Next Year Forecast)
        g2 = (fy2_eps / abs(fy1_eps) - 1) if fy1_eps and fy1_eps != 0 and fy2_eps is not None else None
        unified_eps.append({"period": f"FY {fy2_yr}", "avg": fy2_eps, "growth": g2, "status": "estimate"})
        
        g2r = (fy2_rev / abs(fy1_rev) - 1) if fy1_rev and fy1_rev != 0 and fy2_rev is not None else None
        unified_rev.append({"period": f"FY {fy2_yr}", "avg": fy2_rev, "growth": g2r, "status": "estimate"})


        # (Anomaly healing removed: with proper FY0/FY1 from Yahoo, no longer needed)


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

        # v258: Unified Growth detection from Reformed Table
        eps_forward_growth = info.get('earningsGrowth', 0.10)
        if g1 is not None and g2 is not None:
            eps_forward_growth = (g1 + g2) / 2
        elif g1 is not None:
            eps_forward_growth = g1
        elif g2 is not None:
            eps_forward_growth = g2


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
            # v188: Enforce arithmetic mean of FY1 & FY2 estimates (eps_forward_growth)
            # over Yahoo's buggy LTG estimate.
            "eps_5yr_growth": eps_forward_growth,
            "eps_growth_5y_consensus": eps_growth_5y_consensus,
            "eps_estimates":  unified_eps,
            "rev_estimates":  unified_rev,
            "eps_growth": eps_forward_growth,
            "fwd_pe": (current_price / fy1_eps) if (current_price and fy1_eps and fy1_eps > 0) else None, # v260
            "eps_trend": eps_trend
        }


    except Exception as e:
        import traceback
        print(f"[Analyst] Data fetch failed for {ticker_symbol}: {e}")
        print(traceback.format_exc())
        return {"ticker": ticker_symbol.upper(), "error": str(e)}
