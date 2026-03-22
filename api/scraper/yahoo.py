import yfinance as yf
import os
import datetime
import urllib.request
import urllib.parse
import json
import concurrent.futures
import time
import random
import requests
import pandas as pd

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

def get_fx_rate(info: dict) -> float:
    """Detects currency mismatch and fetches dynamic FX rate from Yahoo."""
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

def get_nasdaq_earnings_growth(ticker: str, trailing_eps: float) -> float:
    """
    Fetches multi-year forward earnings growth estimates from Nasdaq.
    Targets the 3-year horizon (e.g., 2027-2029) to calculate a CAGR.
    """
    if not trailing_eps or trailing_eps <= 0:
        return None
    try:
        url = f'https://api.nasdaq.com/api/analyst/{ticker.upper()}/earnings-forecast'
        req = urllib.request.Request(url, headers={'User-Agent': get_random_agent()})
        with urllib.request.urlopen(req) as response:
            raw_data = response.read()
            data = json.loads(raw_data)
            
        rows = data.get('data', {}).get('yearlyForecast', {}).get('rows', [])
        if rows and len(rows) > 1:
            # Consistent with Non-GAAP Estimates: 
            # Calculate CAGR between the Forecast Years themselves if available.
            # This avoids the GAAP (Trailing) vs Non-GAAP (Forecast) mismatch.
            base_row = rows[0]
            base_eps = float(base_row.get('consensusEPSForecast', 0))
            
            if base_eps > 0:
                # Target the furthest available year up to index 3 (usually 4th year from now)
                target_idx = min(len(rows) - 1, 3)
                target_row = rows[target_idx]
                target_eps = float(target_row.get('consensusEPSForecast', 0))
                
                if target_eps > 0:
                    # Years = gap between target index and base index 0
                    years = target_idx
                    if years > 0:
                        cagr = (target_eps / base_eps) ** (1 / years) - 1
                        return cagr

            # Fallback to CAGR from Trailing EPS to the first Forecast Year if only 1 row or base failed
            target_eps = float(rows[0].get('consensusEPSForecast', 0))
            if target_eps > 0:
                # Row 0 is roughly 1 year out from Trailing
                return (target_eps / trailing_eps) - 1

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
        with urllib.request.urlopen(req) as response:
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
                return total_eps
    except Exception as e:
        print(f"Error fetching Nasdaq Actual EPS for {ticker}: {e}")
    return None

def calculate_historic_pe(stock, financials):
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
        
        pe_ratios = []
        for date, eps in eps_values.items():
            if eps <= 0: # Skip negative/zero EPS for P/E average
                continue
            
            # Fetch price around the fiscal year end date
            try:
                # Use a small window to ensure we get a trading day price
                start_date = date - pd.Timedelta(days=10)
                end_date = date + pd.Timedelta(days=1)
                hist = stock.history(start=start_date, end=end_date)
                
                if not hist.empty:
                    # Get the price closest to the target date (usually the last available in window)
                    price = float(hist['Close'].iloc[-1])
                    pe_ratios.append(price / eps)
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
    Returns a mapping from '0q', '+1q', '0y', '+1y' to human-readable 
    labels like 'Q1 2026', 'FY 2026' based on fiscal year end.
    """
    now = datetime.datetime.now()
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

def get_company_data(ticker_symbol: str):
    """
    Fetches comprehensive data from Yahoo Finance as the primary/fallback data source.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # Parallelize data fetching using ThreadPoolExecutor
        # fetching info, cashflow, financials, and balance_sheet simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
            future_info = executor.submit(lambda: stock.info)
            future_cf = executor.submit(lambda: stock.cashflow)
            future_fin = executor.submit(lambda: stock.financials)
            future_bs = executor.submit(lambda: stock.balance_sheet)
            future_qcf = executor.submit(lambda: stock.quarterly_cashflow)
            future_qfin = executor.submit(lambda: stock.quarterly_income_stmt)
            future_divs = executor.submit(lambda: stock.dividends)
            
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

        # 0. FX Normalization (Dynamic conversion for ADRs)
        fx_rate = get_fx_rate(info)

        # Basic Price and Identifying Info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        name = info.get('shortName', ticker_symbol)
        sector = info.get('sector')
        industry = info.get('industry')
        
        # Start background fetches while processing info
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as nasdaq_executor:
            # Note: Nasdaq growth is now a 3Y CAGR
            future_nasdaq_cagr = nasdaq_executor.submit(get_nasdaq_earnings_growth, ticker_symbol, info.get('trailingEps'))
            # Fetch actual Non-GAAP EPS as fallback for GAAP trailingEps
            future_nasdaq_actual = nasdaq_executor.submit(get_nasdaq_actual_eps, ticker_symbol)
            future_est = nasdaq_executor.submit(lambda: stock.earnings_estimate)
            future_growth_est = nasdaq_executor.submit(lambda: stock.growth_estimates)

            # Valuation Multiples & EPS (Normalize EPS)
            trailing_eps = (info.get('trailingEps') or info.get('epsTrailingTwelveMonths', 0)) * fx_rate
            forward_eps = (info.get('forwardEps') or 0) * fx_rate
            pe_ratio = info.get('trailingPE') # Ratio: no conversion
            if not pe_ratio and current_price and trailing_eps and trailing_eps > 0:
                pe_ratio = current_price / trailing_eps
            forward_pe = info.get('forwardPE') # Ratio: no conversion
            ps_ratio = info.get('priceToSalesTrailing12Months') # Ratio: no conversion
            
            eps_growth = None
            eps_growth_period = None

            # 1. Try YF earnings_estimate - HIGHEST PRIORITY for consensus-based valuation
            try:
                ef = future_est.result(timeout=2)
                if ef is not None and not ef.empty:
                    # Smart selection: pick healthiest forward year (+5y -> +1y -> 0y)
                    g_5y = ef.loc['+5y'].get('growth') if '+5y' in ef.index else None
                    g_1y = ef.loc['+1y'].get('growth') if '+1y' in ef.index else None
                    g_0y = ef.loc['0y'].get('growth') if '0y' in ef.index else None
                    
                    labels = get_period_labels(info)
                    
                    if g_5y is not None:
                        eps_growth = float(g_5y)
                        eps_growth_period = labels.get('+5y', 'Next 5 Years (Est)')
                    elif g_1y is not None:
                        eps_growth = float(g_1y)
                        eps_growth_period = labels.get('+1y', 'Next Year (Est)')
                    elif g_0y is not None and g_0y > 0.02:
                        eps_growth = float(g_0y)
                        eps_growth_period = labels.get('0y', 'Current Year (Est)')
            except Exception:
                pass
            
            # 1.5 Try YF growth_estimates (Analysis tab - Next 5 Years)
            eps_growth_5y_consensus = None
            try:
                ge = future_growth_est.result(timeout=2)
                if ge is not None and not ge.empty:
                    if 'Next 5 Years' in ge.index:
                        # Columns are [Ticker, 'S&P 500']
                        val = ge.loc['Next 5 Years', ge.columns[0]]
                        if val is not None and not pd.isna(val):
                            eps_growth_5y_consensus = float(val)
            except Exception:
                pass

            # 2. Try Nasdaq growth (fallback)
            nasdaq_growth_3y = None
            nasdaq_actual_eps = None
            try:
                nasdaq_growth_3y = future_nasdaq_cagr.result(timeout=5)
                nasdaq_actual_eps = future_nasdaq_actual.result(timeout=5)
            except Exception:
                pass

            # Update trailing_eps if Nasdaq Actual (Non-GAAP) is found and significantly different
            if nasdaq_actual_eps is not None:
                current_trailing = info.get('trailingEps')
                # If GAAP (YF) is > 20% different from Non-GAAP (Nasdaq), prefer Non-GAAP
                if not current_trailing or abs(nasdaq_actual_eps - current_trailing) / max(current_trailing, 1) > 0.20:
                    info['trailingEps'] = nasdaq_actual_eps
                    trailing_eps = nasdaq_actual_eps

            if eps_growth is None:
                eps_growth = eps_growth_5y_consensus or nasdaq_growth_3y
                if eps_growth: 
                    eps_growth_period = "Analyst 5Y Cons." if eps_growth_5y_consensus else "Nasdaq 3Y Forecast"

            # 3. Fallback to info.get('earningsGrowth')
            if eps_growth is None:
                eps_growth = info.get('earningsGrowth')
                eps_growth_period = "Trailing Growth"
                if not eps_growth and forward_eps and trailing_eps and trailing_eps > 0:
                    eps_growth = (forward_eps - trailing_eps) / trailing_eps
                elif not eps_growth:
                    eps_growth = info.get('revenueGrowth', 0.05)
            
        # Financials for DCF & Margins (Wait for results)
        try:
            financials = future_fin.result(timeout=10)
            if financials is not None and fx_rate != 1.0: financials = financials * fx_rate
        except Exception:
            financials = None
        try:
            cashflow = future_cf.result(timeout=10)
            if cashflow is not None and fx_rate != 1.0: cashflow = cashflow * fx_rate
        except Exception:
            cashflow = None
        try:
            bs = future_bs.result(timeout=10)
            if bs is not None and fx_rate != 1.0: bs = bs * fx_rate
        except Exception:
            bs = None
        try:
            q_financials = future_qfin.result(timeout=10)
            if q_financials is not None and fx_rate != 1.0: q_financials = q_financials * fx_rate
        except Exception:
            q_financials = None
        try:
            q_cashflow = future_qcf.result(timeout=10)
            if q_cashflow is not None and fx_rate != 1.0: q_cashflow = q_cashflow * fx_rate
        except Exception:
            q_cashflow = None
        
        try:
            dividends_raw = future_divs.result(timeout=10)
        except Exception:
            dividends_raw = pd.Series()
        peg_ratio = None
        if pe_ratio and eps_growth and eps_growth > 0:
            peg_ratio = pe_ratio / (eps_growth * 100)
        
        if not peg_ratio:
            peg_ratio = info.get('pegRatio') or info.get('trailingPegRatio')
            
        # Financials for DCF & Margins (Prefer normalized DataFrames over info.get for ADR reliability)
        fcf = None
        try:
            if cashflow is not None and not cashflow.empty:
                if 'Free Cash Flow' in cashflow.index:
                    fcf = float(cashflow.loc['Free Cash Flow'].iloc[0])
                elif 'Operating Cash Flow' in cashflow.index:
                    fcf = float(cashflow.loc['Operating Cash Flow'].iloc[0])
        except: pass
        
        if fcf is None:
            fcf = info.get('freeCashflow')
            if fcf is None: fcf = info.get('operatingCashflow')
            if fcf is not None: fcf *= fx_rate
            
        shares_outstanding = info.get('sharesOutstanding') # No convert
        
        total_cash = (info.get('totalCash') or 0) * fx_rate
        total_debt = (info.get('totalDebt') or 0) * fx_rate
        
        gross_margins = info.get('grossMargins') # Ratio
        profit_margins = info.get('profitMargins') # Ratio
        
        revenue = None
        try:
            if financials is not None and not financials.empty:
                if 'Total Revenue' in financials.index:
                    revenue = float(financials.loc['Total Revenue'].iloc[0])
        except: pass
        
        if revenue is None:
            revenue = (info.get('totalRevenue') or 0) * fx_rate
            
        market_cap = info.get('marketCap') # Price * Shares: usually USD for US-listed ADR

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
        dividend_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield')
        payout_ratio = info.get('payoutRatio')

        # FCF Trend
        fcf_history = []
        historic_fcf_growth = None
        try:
            if cashflow is not None and not cashflow.empty:
                fcf_y = []
                if 'Free Cash Flow' in cashflow.index:
                    fcf_y = cashflow.loc['Free Cash Flow'].dropna().head(5).tolist()
                elif 'Operating Cash Flow' in cashflow.index:
                    fcf_y = cashflow.loc['Operating Cash Flow'].dropna().head(5).tolist()
                
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
                indices = financials.index
                eps_row = None
                if 'Diluted EPS' in indices: eps_row = financials.loc['Diluted EPS']
                elif 'Basic EPS' in indices: eps_row = financials.loc['Basic EPS']
                
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

        # Historic Buyback Rate
        historic_buyback_rate = None
        try:
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
                
                # If we have no dividends in the current or previous year, the streak is dead
                if latest_div_year >= this_year - 1:
                    for i in range(len(div_years) - 1):
                        curr_yr = div_years[i]
                        prev_yr = div_years[i+1]
                        # if dividend is mostly >= prev year, streak continues
                        if div_annual[curr_yr] >= div_annual[prev_yr] * 0.98: 
                            current_streak += 1
                        else:
                            break
                dividend_streak = current_streak
                
                # 5Y CAGR: (DivCurr / Div_5Y_Ago) ^ (1/5) - 1
                if len(div_annual) >= 6:
                    latest_val = div_annual.iloc[-1]
                    old_val = div_annual.iloc[-6]
                    if old_val > 0 and latest_val > 0:
                        # 5-year CAGR usually means 5 intervals (e.g. 2024/2019)
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

        # 1. Historical Trends (Annual) for Table
        historical_trends = []
        try:
            if financials is not None and not financials.empty and cashflow is not None and not cashflow.empty:
                cols = list(set(financials.columns).intersection(cashflow.columns))
                cols = sorted(cols, reverse=True)
                years_trends = cols[:10]
                for year in years_trends:
                    rev = float(financials.loc['Total Revenue', year]) if 'Total Revenue' in financials.index and not pd.isna(financials.loc['Total Revenue', year]) else None
                    ni = float(financials.loc['Net Income', year]) if 'Net Income' in financials.index and not pd.isna(financials.loc['Net Income', year]) else None
                    fcf_v = float(cashflow.loc['Free Cash Flow', year]) if 'Free Cash Flow' in cashflow.index and not pd.isna(cashflow.loc['Free Cash Flow', year]) else None
                    margin = (ni / rev) if (ni and rev and rev > 0) else None
                    year_str = year.year if hasattr(year, 'year') else str(year)[:4]
                    
                    if rev or margin or fcf_v:
                        historical_trends.append({
                            "year": year_str,
                            "revenue": rev,
                            "net_margin": margin,
                            "fcf": fcf_v
                        })
        except Exception as e:
            print(f"Historical trends format issue: {e}")

        # 2. Historical & Projected Data for Charts (Annual)
        historical_data = {
            "years": [],
            "revenue": [],
            "eps": [],
            "fcf": [],
            "shares": []
        }
        try:
            # 2a. Actual Historical Data
            if financials is not None and not financials.empty:
                # Get the most recent ~5 years, chronologically
                common_cols = sorted(list(set(financials.columns).intersection(cashflow.columns)))
                target_years = common_cols[-5:]
                
                for yr in target_years:
                    rev_val = financials.loc['Total Revenue', yr] if 'Total Revenue' in financials.index else None
                    eps_val = financials.loc['Diluted EPS', yr] if 'Diluted EPS' in financials.index else (financials.loc['Basic EPS', yr] if 'Basic EPS' in financials.index else None)
                    fcf_val = cashflow.loc['Free Cash Flow', yr] if 'Free Cash Flow' in cashflow.index else None
                    
                    # Convert to float safely
                    r = float(rev_val) if not pd.isna(rev_val) else 0
                    e = float(eps_val) if not pd.isna(eps_val) else 0
                    f = float(fcf_val) if not pd.isna(fcf_val) else 0
                    
                    # Skip year if all key metrics are zero (e.g. 2021 bug reported by user)
                    if r == 0 and e == 0 and f == 0:
                        continue

                    share_val = None
                    for sk in ['Basic Average Shares', 'Diluted Average Shares', 'Ordinary Shares Number']:
                        if sk in financials.index:
                            share_val = financials.loc[sk, yr]
                            if not pd.isna(share_val): break
                    
                    yr_label = str(yr.year) if hasattr(yr, 'year') else str(yr)[:4]
                    
                    historical_data["years"].append(yr_label)
                    historical_data["revenue"].append(r)
                    historical_data["eps"].append(e)
                    historical_data["fcf"].append(f)
                    historical_data["shares"].append(float(share_val) if share_val and not pd.isna(share_val) else 0)

            # 2b. Add Projections (Next 2 FYs)
            try:
                # Use analyst estimates already fetched if possible, or fetch now
                # We'll re-fetch a bit of info to be safe
                stock = yf.Ticker(ticker_symbol)
                ee = stock.earnings_estimate
                re = stock.revenue_estimate
                
                # Identify current year and next year targets
                this_fy = datetime.datetime.now().year
                next_fy = this_fy + 1
                
                for fy in [this_fy, next_fy]:
                    fy_code = f"0y" if fy == this_fy else "+1y"
                    label = f"{fy} (Est)"
                    
                    # Fetch EPS Est
                    eps_est = None
                    if ee is not None and not ee.empty:
                        # Find the row for this FY
                        if fy_code in ee.index:
                            val = ee.loc[fy_code, 'avg']
                            eps_est = val * fx_rate if val is not None else None
                    
                    # Fetch Rev Est
                    rev_est = None
                    if re is not None and not re.empty:
                        if fy_code in re.index:
                            val = re.loc[fy_code, 'avg']
                            rev_est = val * fx_rate if val is not None else None
                    
                    # Project FCF (Simple proxy: apply same growth as revenue to latest FCF)
                    proj_fcf = 0
                    if rev_est and revenue and historical_data["revenue"]:
                        last_actual_rev = historical_data["revenue"][-1]
                        last_actual_fcf = historical_data["fcf"][-1]
                        if last_actual_rev > 0:
                            proj_fcf = last_actual_fcf * (rev_est / last_actual_rev)
                    
                    if eps_est or rev_est:
                        historical_data["years"].append(label)
                        historical_data["revenue"].append(float(rev_est) if rev_est and not pd.isna(rev_est) else 0)
                        historical_data["eps"].append(float(eps_est) if eps_est and not pd.isna(eps_est) else 0)
                        historical_data["fcf"].append(float(proj_fcf))
                        historical_data["shares"].append(historical_data["shares"][-1] if historical_data["shares"] else 0)

            except Exception as e_proj:
                print(f"Error adding projections to charts: {e_proj}")

        except Exception as e:
            print(f"Error extracting historical_data: {e}")

        # Calculate Historic PE (5-Year Average)
        pe_historic = calculate_historic_pe(stock, financials)

        # 4. New Profile Metrics (User Requested Logic)
        summary_raw = info.get('longBusinessSummary')
        if summary_raw:
            # Join first 2 sentences and add a dot
            business_summary = '. '.join(summary_raw.split('. ')[:2]).strip()
            if not business_summary.endswith('.'):
                business_summary += '.'
        else:
            business_summary = 'Description not available.'
        
        op_margin = info.get('operatingMargins')
        net_margin = info.get('profitMargins')
        payout = info.get('payoutRatio')
        insider = info.get('heldPercentInsiders')
        
        earnings_ts = info.get('earningsTimestamp') or info.get('earningsTimestampStart')
        next_earnings_date = None
        if earnings_ts:
            try:
                dt = datetime.datetime.fromtimestamp(earnings_ts)
                month = dt.month
                year = dt.year
                # Logic to deduce Reported Quarter based on month
                if 1 <= month <= 3:
                    q_label = "Q4"
                    q_year = year - 1
                elif 4 <= month <= 6:
                    q_label = "Q1"
                    q_year = year
                elif 7 <= month <= 9:
                    q_label = "Q2"
                    q_year = year
                else:
                    q_label = "Q3"
                    q_year = year
                next_earnings_date = f"{q_label} {q_year} ({dt.strftime('%d.%m.%Y')})"
            except Exception:
                next_earnings_date = None
        
        # Fallback for Missing Next Earnings Date (using stock.earnings_dates)
        if not next_earnings_date:
            try:
                ed = stock.earnings_dates
                if ed is not None and not ed.empty:
                    # Filter for future dates only
                    now = datetime.datetime.now(datetime.timezone.utc)
                    future_dates = ed[ed.index > now]
                    if not future_dates.empty:
                        # Take the soonest one (index is usually descending, so take last or sort)
                        soonest = future_dates.sort_index().index[0]
                        month = soonest.month
                        year = soonest.year
                        if 1 <= month <= 3:
                            q_label = "Q4"
                            q_year = year - 1
                        elif 4 <= month <= 6:
                            q_label = "Q1"
                            q_year = year
                        elif 7 <= month <= 9:
                            q_label = "Q2"
                            q_year = year
                        else:
                            q_label = "Q3"
                            q_year = year
                        next_earnings_date = f"{q_label} {q_year} ({soonest.strftime('%d.%m.%Y')})"
            except Exception as e_ed:
                print(f"Earnings fallback error: {e_ed}")

        return {
            "pe_historic": pe_historic,
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
            "eps_growth_3y": historic_eps_growth_3y,
            "eps_growth_5y": historic_eps_growth_5y,
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
            "payout_ratio": payout, # Use payout from new logic
            "historic_eps_growth": historic_eps_growth,
            "historical_trends": historical_trends,
            "roe": roe,
            "roa": roa,
            "price_to_book": price_to_book,
            "operating_cashflow": operating_cashflow,
            "historical_data": historical_data,
            "forward_eps": forward_eps,
            "ebit_margin": ebit_margin,
            "operating_margin": op_margin, # Singular as requested
            "net_margin": net_margin,
            "business_summary": business_summary,
            "insider_ownership": insider,
            "next_earnings_date": next_earnings_date,
            "fwd_ps": fwd_ps,
            "next_3y_rev_est": next_3y_rev_est,
            "beta": info.get('beta'),
            "dividend_streak": dividend_streak,
            "dividend_cagr_5y": dividend_cagr_5y,
            "red_flags": red_flags,
            "earnings_growth_est": info.get('earningsGrowth'),
            "revenue_growth_est": info.get('revenueGrowth'),
            "eps_growth_5y_consensus": eps_growth_5y_consensus,
            "eps_growth_nasdaq_3y": nasdaq_growth_3y
        }
    except Exception as e:
        print(f"Error fetching Yahoo Data for {ticker_symbol}: {e}")
        return None

def get_competitors_data(target_ticker: str, sector: str, target_industry: str, target_market_cap: float = 0, limit: int = 3) -> list:
    """
    Find relevant industry peers using Finnhub API or dynamic Yahoo fallback.
    """
    try:
        target_ticker = target_ticker.upper()
        
        FINNHUB_KEY = os.environ.get('FINNHUB_API_KEY')
        
        peers = []

        if FINNHUB_KEY:
            # 1. Try Finnhub
            try:
                url = f"https://finnhub.io/api/v1/stock/peers?symbol={target_ticker}&token={FINNHUB_KEY}"
                resp = requests.get(url, timeout=10)
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
                resp = requests.get(url, headers=headers, timeout=10)
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

        # 2. Universal Scraper Fallback (if still nothing)
        if not peers:
            print(f"No peers for {target_ticker}, attempting scraping fallback...")
            try:
                headers = {'User-Agent': random.choice(USER_AGENTS)}
                url = f"https://finance.yahoo.com/quote/{target_ticker}/"
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    import re
                    ignore = {'GSPC', 'DJI', 'IXIC', 'RUT', 'TNX', 'VIX', target_ticker}
                    found = []
                    # Look for tickers in common Yahoo Finance patterns
                    patterns = [
                        r'/quote/([A-Z]{1,5})/',                       # Standard tickers
                        r'symbol":"([A-Z]{1,5})"',                    # JSON-embedded symbols
                        r'data-symbol="([A-Z]{1,5})"',                 # Data attributes
                        r'symbol">([A-Z]{1,5})</span>',                # Span content
                        r'data-symbol=\"([A-Z0-9\.-]+)\"',             # Pattern 3: data-symbol attributes (more robust)
                        r'/quote/([A-Z0-9\.-]+)\?'                     # Pattern 4: Link patterns like /quote/AAPL?
                    ]
                    found_set = set()
                    for pattern in patterns:
                        matches = re.findall(pattern, resp.text)
                        for m in matches:
                            # Allow alphanumeric, dots, and hyphens for more robust ticker matching
                            if m not in ignore and re.match(r'^[A-Z0-9\.-]+$', m) and m not in found_set:
                                found_set.add(m)
                                found.append(m)
                                if len(found) >= 15: break
                        if len(found) >= 15: break
                    peers = found[:15]
            except Exception as e_scrape:
                print(f"Scraping fallback error: {e_scrape}")

        if not peers:
            return []

        # 2. Extract and Validate Peers by Sector
        final_peers = []
        target_sector = sector
        target_industry = target_industry
        
        # Deduplicate and exclude self/similar companies (GOOG vs GOOGL)
        candidates = []
        try:
            target_info = yf.Ticker(target_ticker).info
            target_name_base = (target_info.get('shortName') or target_info.get('longName') or target_ticker).lower()
        except:
            target_name_base = target_ticker.lower()
        
        seen_tickers = {target_ticker.upper()}
        seen_roots = {target_ticker.upper()[:3]}  # Root-based dedup (e.g., GOO for GOOG/GOOGL)
        
        for p in peers:
            p_upper = p.upper()
            if p_upper in seen_tickers:
                continue
            
            # Basic ticker root check (GOOG vs GOOGL, BRK.A vs BRK.B)
            if p_upper.startswith(target_ticker.upper()) or target_ticker.upper().startswith(p_upper):
                continue
            
            # Cross-peer root dedup: if a shorter ticker with the same root already exists, skip
            p_root = p_upper[:3]
            if len(p_upper) > 3 and p_root in seen_roots:
                continue
                
            candidates.append(p_upper)
            seen_tickers.add(p_upper)
            seen_roots.add(p_root)

        print(f"Validating {len(candidates)} candidates for sector: {target_sector}")

        # Pass 1: Strict Industry Match
        for ticker in candidates:
            if len(final_peers) >= limit:
                break
            try:
                data = get_lightweight_company_data(ticker)
                if not data or not data.get('ticker'):
                    continue
                peer_industry = data.get('industry')
                if target_industry and peer_industry:
                    t_ind_norm = target_industry.lower().strip()
                    p_ind_norm = peer_industry.lower().strip()
                    
                    # Robust matching: check for significant keyword overlap
                    # We ignore common filler words like 'and', 'services', 'products'
                    ignore_words = {'and', 'services', 'products', 'equipment', 'manufacturing', 'technology', 'information'}
                    t_keywords = {w for w in t_ind_norm.replace(' - ', ' ').replace(',', ' ').split() if w not in ignore_words}
                    p_keywords = {w for w in p_ind_norm.replace(' - ', ' ').replace(',', ' ').split() if w not in ignore_words}
                    
                    # Direct partial match (e.g. 'Software - Application' vs 'Software')
                    direct_match = t_ind_norm in p_ind_norm or p_ind_norm in t_ind_norm
                    # Keyword intersection (at least one significant word matches)
                    keyword_match = bool(t_keywords & p_keywords)
                    
                    if direct_match or keyword_match:
                        final_peers.append(data)
            except Exception as e:
                print(f"Error validating peer {ticker}: {e}")
                continue

        # Pass 2: Broader Sector Match + Soft Industry Check
        if len(final_peers) < limit:
            for ticker in candidates:
                if len(final_peers) >= limit:
                    break
                # Skip if already added
                if any(p.get('ticker') == ticker for p in final_peers):
                    continue
                try:
                    data = get_lightweight_company_data(ticker)
                    if not data or not data.get('ticker'):
                        continue
                        
                    peer_sector = data.get('sector')
                    peer_industry = data.get('industry')
                    
                    if target_sector and peer_sector == target_sector:
                        # Soft Industry Match to prevent ridiculous cross-sector pairings
                        if target_industry and peer_industry:
                            t_ind = target_industry.lower()
                            p_ind = peer_industry.lower()
                            
                            # Software shouldn't match Chips/Hardware
                            if 'software' in t_ind and 'software' not in p_ind:
                                continue
                            if 'semiconductor' in t_ind and 'semiconductor' not in p_ind:
                                continue
                            # Autos shouldn't match E-Commerce/Retail (fixes TSLA matching AMZN)
                            if 'auto' in t_ind and 'auto' not in p_ind:
                                continue
                                
                        final_peers.append(data)
                except Exception as e:
                    print(f"Error validating peer fallback {ticker}: {e}")
                    continue

        # Pass 3: Ultimate Fallback - Any Candidate from the same Sector (last resort)
        if len(final_peers) < limit:
            for ticker in candidates:
                if len(final_peers) >= limit:
                    break
                if any(p.get('ticker') == ticker for p in final_peers):
                    continue
                try:
                    data = get_lightweight_company_data(ticker)
                    if not data or not data.get('ticker'):
                        continue
                    if target_sector and data.get('sector') == target_sector:
                        final_peers.append(data)
                except:
                    continue

        return final_peers
        
    except Exception as e:
        print(f"Global competitors failure for {target_ticker}: {e}")
        return []

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
            "eps": info.get('trailingEps'),
            "margin": info.get('operatingMargins'),
            "market_cap": info.get('marketCap') or info.get('regularMarketCap'),
            "industry": info.get('industry'),
            "sector": info.get('sector')
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
        return {"trailing_pe": 20.0, "forward_pe": 18.0}
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
                            "period": date_str, "avg": val * fx_rate, "status": "reported",
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
                        "period": date_str, "avg": float(rev_act) * fx_rate, "status": "reported", "surprise_pct": None
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
                    val_unscaled = float(avg) if avg is not None and not (isinstance(avg, float) and pd.isna(avg)) else None
                    eps_estimates.append({
                        "period": labels.get(p_key, p_key), "period_code": p_key,
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
                    rev_estimates.append({
                        "period": labels.get(p_key, p_key), "period_code": p_key,
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
        
        # New: 5 year analyst consensus from "Analysis" tab (via yfinance.growth_estimates)
        eps_growth_5y_consensus = None
        try:
            ge = stock.growth_estimates
            if ge is not None and not ge.empty:
                # Some companies use 'LTG' (Long Term Growth) instead of 'Next 5 Years'
                target_labels = ['Next 5 Years', 'LTG']
                val = None
                for lbl in target_labels:
                    if lbl in ge.index:
                        val = ge.loc[lbl, ge.columns[0]]
                        if val is not None and not pd.isna(val):
                            break
                            
                if val is not None and not pd.isna(val):
                    eps_growth_5y_consensus = float(val)
        except:
            pass

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
            "eps_5yr_growth": eps_growth_5y_consensus if eps_growth_5y_consensus is not None else eps_forward_growth,
            "eps_growth_5y_consensus": eps_growth_5y_consensus,
            "eps_estimates":  unified_eps,
            "rev_estimates":  unified_rev
        }

    except Exception as e:
        print(f"[Analyst] Data fetch failed for {ticker_symbol}: {e}")
        return {"ticker": ticker_symbol.upper(), "error": str(e)}
