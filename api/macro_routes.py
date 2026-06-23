from fastapi import APIRouter
from cachetools import TTLCache, cached
from threading import Lock
from bs4 import BeautifulSoup
import requests
import json
import yfinance as yf
from functools import wraps

router = APIRouter()

# Cache macro data for 24 hours
macro_cache_v5 = TTLCache(maxsize=10, ttl=86400)

def safe_cached(cache, fallback_value=None, lock=None):
    """
    Thread-safe caching decorator that avoids caching fallback values.
    """
    if lock is None:
        lock = Lock()
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            with lock:
                if key in cache:
                    return cache[key]

            result = func(*args, **kwargs)

            # Simple heuristic to check if result is a fallback
            if result != fallback_value and result is not None:
                with lock:
                    cache[key] = result
            return result
        return wrapper
    return decorator

@safe_cached(cache=TTLCache(maxsize=1, ttl=86400), fallback_value={"score": 50, "rating": "neutral"})
def get_fear_and_greed():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        r = requests.get('https://production.dataviz.cnn.io/index/fearandgreed/graphdata', headers=headers, timeout=10)
        data = r.json()
        score = data.get('fear_and_greed', {}).get('score', 50)
        rating = data.get('fear_and_greed', {}).get('rating', 'neutral')
        return {"score": round(score), "rating": rating}
    except Exception as e:
        print(f"Error fetching Fear & Greed: {e}")
        return {"score": 50, "rating": "neutral"}


@safe_cached(cache=TTLCache(maxsize=20, ttl=86400), fallback_value=[])
def get_etf_holdings(ticker_symbol):
    try:
        tkr = yf.Ticker(ticker_symbol)
        holdings = tkr.funds_data.top_holdings
        if holdings.empty:
            return []

        res = []
        for sym, row in holdings.iterrows():
            # Guessing domain as example.com as fallback isn't needed anymore if we can't guess
            # Actually frontend has fallbacks if domain is example.com it tries clearbit then ui-avatars.
            # We will use 'example.com' to trigger those fallbacks.
            res.append({
                "company": row['Name'],
                "ticker": sym,
                "weight": f"{row['Holding Percent'] * 100:.2f}%",
                "domain": "example.com"
            })
        return res
    except Exception as e:
        print(f"Error fetching ETF holdings for {ticker_symbol}: {e}")
        return []

def get_static_etf_top10(index_name):
    # Mapping for live fetching
    ticker_map = {
        "sp500": "SPY",
        "nasdaq": "QQQ",
        "russell": "IWM",
        "dax": "EXS1.DE",
        "dow": "DIA",
        "stoxx": "FEZ"
    }

    if index_name in ticker_map:
        live_data = get_etf_holdings(ticker_map[index_name])
        if live_data:
            return live_data

    # Fallback to static data
    if index_name == "sp500":
        return [
            {"company": "Microsoft", "ticker": "MSFT", "weight": "7.1%", "domain": "microsoft.com"},
            {"company": "Apple", "ticker": "AAPL", "weight": "6.5%", "domain": "apple.com"},
            {"company": "NVIDIA", "ticker": "NVDA", "weight": "6.1%", "domain": "nvidia.com"},
            {"company": "Amazon", "ticker": "AMZN", "weight": "3.5%", "domain": "amazon.com"},
            {"company": "Meta", "ticker": "META", "weight": "2.2%", "domain": "meta.com"},
            {"company": "Alphabet (Class A)", "ticker": "GOOGL", "weight": "2.1%", "domain": "abc.xyz"},
            {"company": "Alphabet (Class C)", "ticker": "GOOG", "weight": "1.8%", "domain": "abc.xyz"},
            {"company": "Berkshire Hathaway", "ticker": "BRK.B", "weight": "1.7%", "domain": "berkshirehathaway.com"},
            {"company": "Broadcom", "ticker": "AVGO", "weight": "1.3%", "domain": "broadcom.com"},
            {"company": "Eli Lilly", "ticker": "LLY", "weight": "1.3%", "domain": "lilly.com"}
        ]
    elif index_name == "nasdaq":
        return [
            {"company": "Microsoft", "ticker": "MSFT", "weight": "8.5%", "domain": "microsoft.com"},
            {"company": "Apple", "ticker": "AAPL", "weight": "8.2%", "domain": "apple.com"},
            {"company": "NVIDIA", "ticker": "NVDA", "weight": "6.9%", "domain": "nvidia.com"},
            {"company": "Amazon", "ticker": "AMZN", "weight": "4.9%", "domain": "amazon.com"},
            {"company": "Meta", "ticker": "META", "weight": "4.2%", "domain": "meta.com"},
            {"company": "Broadcom", "ticker": "AVGO", "weight": "4.1%", "domain": "broadcom.com"},
            {"company": "Alphabet (Class A)", "ticker": "GOOGL", "weight": "2.6%", "domain": "abc.xyz"},
            {"company": "Alphabet (Class C)", "ticker": "GOOG", "weight": "2.5%", "domain": "abc.xyz"},
            {"company": "Tesla", "ticker": "TSLA", "weight": "2.4%", "domain": "tesla.com"},
            {"company": "Costco", "ticker": "COST", "weight": "2.1%", "domain": "costco.com"}
        ]
    elif index_name == "russell":
        return [
            {"company": "Super Micro Computer", "ticker": "SMCI", "weight": "1.6%", "domain": "supermicro.com"},
            {"company": "MicroStrategy", "ticker": "MSTR", "weight": "1.2%", "domain": "microstrategy.com"},
            {"company": "Carvana", "ticker": "CVNA", "weight": "0.7%", "domain": "carvana.com"},
            {"company": "Comfort Systems USA", "ticker": "FIX", "weight": "0.4%", "domain": "comfortsystemsusa.com"},
            {"company": "Elf Beauty", "ticker": "ELF", "weight": "0.4%", "domain": "elfcosmetics.com"},
            {"company": "Onto Innovation", "ticker": "ONTO", "weight": "0.3%", "domain": "ontoinnovation.com"},
            {"company": "Light & Wonder", "ticker": "LNW", "weight": "0.3%", "domain": "lnw.com"},
            {"company": "Simpson Manufacturing", "ticker": "SSD", "weight": "0.3%", "domain": "strongtie.com"},
            {"company": "Modine Manufacturing", "ticker": "MOD", "weight": "0.3%", "domain": "modine.com"},
            {"company": "Rambus", "ticker": "RMBS", "weight": "0.3%", "domain": "rambus.com"}
        ]
    elif index_name == "dax":
        return [
            {"company": "SAP SE", "ticker": "SAP.DE", "weight": "12.5%", "domain": "sap.com"},
            {"company": "Siemens", "ticker": "SIE.DE", "weight": "9.8%", "domain": "siemens.com"},
            {"company": "Allianz", "ticker": "ALV.DE", "weight": "8.2%", "domain": "allianz.com"},
            {"company": "Airbus", "ticker": "AIR.DE", "weight": "6.8%", "domain": "airbus.com"},
            {"company": "Deutsche Telekom", "ticker": "DTE.DE", "weight": "5.9%", "domain": "telekom.com"},
            {"company": "Munich Re", "ticker": "MUV2.DE", "weight": "4.5%", "domain": "munichre.com"},
            {"company": "Mercedes-Benz", "ticker": "MBG.DE", "weight": "4.2%", "domain": "mercedes-benz.com"},
            {"company": "DHL Group", "ticker": "DHL.DE", "weight": "3.5%", "domain": "dpdhl.com"},
            {"company": "BMW", "ticker": "BMW.DE", "weight": "3.2%", "domain": "bmwgroup.com"},
            {"company": "Infineon", "ticker": "IFX.DE", "weight": "3.1%", "domain": "infineon.com"}
        ]
    elif index_name == "dow":
        return [
            {"company": "UnitedHealth", "ticker": "UNH", "weight": "8.8%", "domain": "uhg.com"},
            {"company": "Goldman Sachs", "ticker": "GS", "weight": "6.8%", "domain": "goldmansachs.com"},
            {"company": "Microsoft", "ticker": "MSFT", "weight": "6.6%", "domain": "microsoft.com"},
            {"company": "Home Depot", "ticker": "HD", "weight": "5.9%", "domain": "homedepot.com"},
            {"company": "Caterpillar", "ticker": "CAT", "weight": "5.5%", "domain": "caterpillar.com"},
            {"company": "Salesforce", "ticker": "CRM", "weight": "4.8%", "domain": "salesforce.com"},
            {"company": "Amgen", "ticker": "AMGN", "weight": "4.7%", "domain": "amgen.com"},
            {"company": "Visa", "ticker": "V", "weight": "4.6%", "domain": "visa.com"},
            {"company": "McDonald's", "ticker": "MCD", "weight": "4.5%", "domain": "mcdonalds.com"},
            {"company": "Boeing", "ticker": "BA", "weight": "3.5%", "domain": "boeing.com"}
        ]
    elif index_name == "stoxx":
        return [
            {"company": "Novo Nordisk", "ticker": "NOVOB.CO", "weight": "3.5%", "domain": "novonordisk.com"},
            {"company": "ASML Holding", "ticker": "ASML.AS", "weight": "3.2%", "domain": "asml.com"},
            {"company": "Nestle", "ticker": "NESN.SW", "weight": "2.8%", "domain": "nestle.com"},
            {"company": "LVMH", "ticker": "MC.PA", "weight": "2.2%", "domain": "lvmh.com"},
            {"company": "Novartis", "ticker": "NOVN.SW", "weight": "2.0%", "domain": "novartis.com"},
            {"company": "AstraZeneca", "ticker": "AZN.L", "weight": "1.9%", "domain": "astrazeneca.com"},
            {"company": "Roche", "ticker": "ROG.SW", "weight": "1.8%", "domain": "roche.com"},
            {"company": "Shell", "ticker": "SHEL.L", "weight": "1.8%", "domain": "shell.com"},
            {"company": "SAP SE", "ticker": "SAP.DE", "weight": "1.7%", "domain": "sap.com"},
            {"company": "TotalEnergies", "ticker": "TTE.PA", "weight": "1.3%", "domain": "totalenergies.com"}
        ]
    return []

@safe_cached(cache=TTLCache(maxsize=1, ttl=86400), fallback_value=15.0)
def get_vix_current():
    try:
        tkr = yf.Ticker('^VIX')
        hist = tkr.history(period="1d")
        if not hist.empty:
            return round(hist['Close'].iloc[-1], 2)
    except Exception as e:
        print(f"Error fetching VIX: {e}")
    return 15.0 # Fallback

@safe_cached(cache=TTLCache(maxsize=1, ttl=86400), fallback_value={"current": "5.25 - 5.50%", "forecast": "--", "cut_probability": "0%", "hike_probability": "0%", "hold_probability": "100%"})
def get_fed_rate():
    current_val = None
    implied_rate = None
    cut_prob = 0
    hike_prob = 0
    hold_prob = 100
    forecast_str = "--"

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        r = requests.get('https://www.federalreserve.gov/releases/h15/', headers=headers, timeout=10)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                if 'Federal funds (effective)' in row.text:
                    cols = row.find_all('td')
                    if len(cols) > 0:
                        val = cols[-1].text.strip()
                        if val:
                            current_val = float(val)
                            break
    except Exception as e:
        print(f"Error fetching Fed Rate: {e}")

    if current_val is not None:
        try:
            import yfinance as yf
            # ZQ=F: 30-Day Federal Funds futures. Price is 100 - average daily rate.
            tkr = yf.Ticker('ZQ=F')
            hist = tkr.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                implied_rate = 100 - price
                forecast_str = f"{round(implied_rate, 2)}%"

                diff = implied_rate - current_val

                # Simple heuristic based on futures
                if diff < -0.10: # More than 10bps cut priced in
                    cut_prob = min(100, round(abs(diff / 0.25) * 100))
                    hold_prob = max(0, 100 - cut_prob)
                elif diff > 0.10: # More than 10bps hike priced in
                    hike_prob = min(100, round(abs(diff / 0.25) * 100))
                    hold_prob = max(0, 100 - hike_prob)
                else:
                    hold_prob = 100
        except Exception as e:
            print(f"Error fetching Fed Forecast: {e}")

    if current_val is not None:
        return {
            "current": f"{current_val}%",
            "forecast": forecast_str,
            "cut_probability": f"{cut_prob}%",
            "hike_probability": f"{hike_prob}%",
            "hold_probability": f"{hold_prob}%"
        }
    
    return {
        "current": "5.25 - 5.50%",
        "forecast": "--",
        "cut_probability": "0%",
        "hike_probability": "0%",
        "hold_probability": "100%"
    }

@safe_cached(cache=TTLCache(maxsize=10, ttl=86400), fallback_value=[])
def get_world_bank_data(indicator, history=False):
    try:
        url = f'http://api.worldbank.org/v2/country/US/indicator/{indicator}?format=json'
        if history:
            url += '&per_page=15'
            
        r = requests.get(url, timeout=10)
        data = r.json()
        if len(data) > 1 and isinstance(data[1], list):
            if history:
                hist_data = []
                for item in data[1]:
                    if item.get('value') is not None and item.get('date'):
                        hist_data.append({"year": item['date'], "value": round(item['value'], 2)})
                hist_data.reverse() # Oldest to newest
                return hist_data
            else:
                for item in data[1]:
                    if item.get('value') is not None:
                        return item['value']
    except Exception as e:
        print(f"Error fetching World Bank {indicator}: {e}")
    return [] if history else None

@safe_cached(cache=TTLCache(maxsize=1, ttl=86399), fallback_value={"ratio": 0, "market_cap_trillions": 0, "gdp_trillions": 0})
def get_buffett_indicator():
    try:
        ratio = 0
        gdp = None
        market_cap = None
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        r = requests.get('https://www.currentmarketvaluation.com/models/buffett-indicator.php', headers=headers, timeout=10)
        from bs4 import BeautifulSoup
        import re
        soup = BeautifulSoup(r.text, 'html.parser')
        
        match_mcap = re.search(r'Total US Stock Market Value = \$([\d\.]+)T', r.text, re.IGNORECASE)
        if match_mcap:
            market_cap = float(match_mcap.group(1)) * 1_000_000_000_000

        match_gdp = re.search(r'Annualized GDP = \$([\d\.]+)T', r.text, re.IGNORECASE)
        if match_gdp:
            gdp = float(match_gdp.group(1)) * 1_000_000_000_000

        if not gdp:
            gdp = get_world_bank_data('NY.GDP.MKTP.CD')
        if not gdp:
            gdp = 28750000000000

        if market_cap and gdp:
            ratio = (market_cap / gdp) * 100
        else:
            match_ratio = re.search(r'current Buffett Indicator value of ([\d\.]+)%', r.text, re.IGNORECASE)
            if match_ratio:
                ratio = float(match_ratio.group(1))
            if ratio == 0:
                return {"ratio": 0, "market_cap_trillions": 0, "gdp_trillions": round(gdp / 1_000_000_000_000, 2)}
            market_cap = (ratio / 100) * gdp
        
        return {
            "ratio": round(ratio, 1),
            "market_cap_trillions": round(market_cap / 1_000_000_000_000, 2),
            "gdp_trillions": round(gdp / 1_000_000_000_000, 2)
        }
    except Exception as e:
        print(f"Error calculating Buffett Indicator: {e}")
        return {"ratio": 0, "market_cap_trillions": 0, "gdp_trillions": 0}

@router.get("/macro")
def get_macro_dashboard():
    if "macro_data" in macro_cache_v5:
        return macro_cache_v5["macro_data"]
        
    fear_greed = get_fear_and_greed()
    sp500 = get_static_etf_top10("sp500")
    nasdaq = get_static_etf_top10("nasdaq")
    russell2000 = get_static_etf_top10("russell")
    dax = get_static_etf_top10("dax")
    dow = get_static_etf_top10("dow")
    stoxx = get_static_etf_top10("stoxx")
    
    buffett = get_buffett_indicator()
    vix = get_vix_current()
    fed_rate = get_fed_rate()
    
    # Economics History (Last ~15 years)
    inflation_hist = get_world_bank_data('FP.CPI.TOTL.ZG', history=True)
    unemployment_hist = get_world_bank_data('SL.UEM.TOTL.ZS', history=True)
    gdp_hist = get_world_bank_data('NY.GDP.MKTP.CD', history=True)
    
    # GDP Evolution (Last year, Est This Year, Est Next Year)
    current_year = 2026
    current_gdp = buffett.get("gdp_trillions", 31.57) * 1_000_000_000_000
    if current_gdp == 0:
        current_gdp = 31570000000000

    gdp_evolution = {
        "last_year": {"year": current_year - 1, "value": current_gdp / 1.025},
        "this_year": {"year": current_year, "value": current_gdp},
        "next_year": {"year": current_year + 1, "value": current_gdp * 1.025}
    }
    
    data = {
        "fear_greed": fear_greed,
        "buffett_indicator": buffett,
        "vix": vix,
        "fed_rate": fed_rate,
        "gdp_evolution": gdp_evolution,
        "inflation_history": inflation_hist,
        "unemployment_history": unemployment_hist,
        "inflation_pct": inflation_hist[-1]['value'] if inflation_hist else 0,
        "unemployment_pct": unemployment_hist[-1]['value'] if unemployment_hist else 0,
        "etfs": {
            "sp500": sp500,
            "nasdaq": nasdaq,
            "russell": russell2000,
            "dax": dax,
            "dow": dow,
            "stoxx": stoxx
        }
    }
    
    macro_cache_v5["macro_data"] = data
    return data

@router.get("/market-live")
@safe_cached(cache=TTLCache(maxsize=1, ttl=60), fallback_value={"vix": 15.0, "indices": {}})
def get_market_live():
    # Fetch real-time data for VIX and indices
    tickers = yf.Tickers('^VIX ^GSPC ^NDX ^RUT ^GDAXI ^DJI ^STOXX')
    live_data = {"vix": 15.0, "indices": {}}
    
    try:
        # VIX
        if '^VIX' in tickers.tickers:
            hist = tickers.tickers['^VIX'].history(period="1d")
            if not hist.empty:
                live_data["vix"] = round(hist['Close'].iloc[-1], 2)
                
        # Indices mapping to our frontend keys
        mapping = {
            '^GSPC': 'sp500',
            '^NDX': 'nasdaq',
            '^RUT': 'russell',
            '^GDAXI': 'dax',
            '^DJI': 'dow',
            '^STOXX': 'stoxx'
        }
        
        for ticker, key in mapping.items():
            if ticker in tickers.tickers:
                hist = tickers.tickers[ticker].history(period="2d") # Need 2 days to get change
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                    change_pct = ((current_price - prev_close) / prev_close) * 100
                    live_data["indices"][key] = {
                        "price": round(current_price, 2),
                        "change_pct": round(change_pct, 2)
                    }
    except Exception as e:
        print(f"Error fetching live market data: {e}")
        
    return live_data

@router.get("/news")
@safe_cached(cache=TTLCache(maxsize=1, ttl=300), fallback_value={"news": []})
def get_latest_news():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        r = requests.get('https://query2.finance.yahoo.com/v1/finance/search?q=stock+market+news&newsCount=15', headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {"news": data.get("news", [])}
        return {"news": []}
    except Exception as e:
        print(f"Error fetching news: {e}")
        return {"news": []}


import xml.etree.ElementTree as ET
import html

@router.get("/wsj-news")
@safe_cached(cache=TTLCache(maxsize=1, ttl=300), fallback_value={"news": []})
def get_wsj_news():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        # 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml' or 'https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml'
        r = requests.get('https://news.google.com/rss/search?q=site:wsj.com+when:7d', headers=headers, timeout=8)
        
        root = ET.fromstring(r.content)
        news_items = []
        
        for item in root.findall('./channel/item'):
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            if title and link:
                news_items.append({
                    "title": html.unescape(title),
                    "link": link,
                    "publisher": "Wall Street Journal",
                    "providerPublishTime": pub_date
                })
        
        return {"news": news_items[:15]}
    except Exception as e:
        print(f"Error fetching WSJ news: {e}")
        return {"news": []}


@router.get("/read-article")
def read_article(url: str, title: str = ""):
    import os, requests
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("gemini")
    if not gemini_key:
        return {"error": "No Gemini API Key available to read article"}
        
    prompt = f"Please search the web for the news article titled '{title}' (URL: {url}). Read it carefully and provide a highly detailed, comprehensive summary of the entire article. Act as an expert journalist: include all key facts, statistics, direct quotes, and the full narrative flow. If you cannot access the exact article due to paywalls, use your search tool to find other reliable news sources reporting on the EXACT SAME EVENT or topic '{title}', and write a comprehensive news report about it. Format the response beautifully using HTML <p> tags for paragraphs. Do not use markdown backticks, just output the HTML directly. Do not include introductory or concluding fluff."
    
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    try:
        models_to_try = ["gemini-1.5-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
        last_error = "Unknown Error"
        for idx, model in enumerate(models_to_try):
            try:
                resp = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}",
                    json=payload, timeout=8.5
                )
                data = resp.json()
                
                if "error" in data:
                    last_error = f"API Error: {data}"
                    if idx < len(models_to_try) - 1:
                        continue
                
                if "candidates" in data and len(data["candidates"]) > 0:
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    if content.startswith('```html'): content = content[7:]
                    if content.startswith('```'): content = content[3:]
                    if content.endswith('```'): content = content[:-3]
                    content = content.strip()

                    return {"text": content}
                
                last_error = f"AI Blocked ({model}). Raw response: {data}"
                if idx < len(models_to_try) - 1:
                    continue
            except requests.exceptions.ReadTimeout as e:
                last_error = f"Timeout ({model})"
                if idx < len(models_to_try) - 1:
                    continue
            except Exception as e:
                last_error = f"Exception ({model}): {str(e)}"
                if idx < len(models_to_try) - 1:
                    continue
                    
        return {"error": f"Toate modelele au esuat sau a expirat timpul. Ultimul motiv: {last_error}"}
    except Exception as e:
        return {"error": str(e)}
