from fastapi import APIRouter
from cachetools import TTLCache
from bs4 import BeautifulSoup
import requests
import json
import yfinance as yf

router = APIRouter()

# Cache macro data for 24 hours
macro_cache = TTLCache(maxsize=10, ttl=86400)

def get_fear_and_greed():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get('https://production.dataviz.cnn.io/index/fearandgreed/graphdata', headers=headers, timeout=10)
        data = r.json()
        score = data.get('fear_and_greed', {}).get('score', 50)
        rating = data.get('fear_and_greed', {}).get('rating', 'neutral')
        return {"score": round(score), "rating": rating}
    except Exception as e:
        print(f"Error fetching Fear & Greed: {e}")
        return {"score": 50, "rating": "neutral (error)"}

def get_static_etf_top10(index_name):
    if index_name == "sp500":
        return [
            {"company": "Microsoft", "ticker": "MSFT", "weight": "7.1%", "domain": "microsoft.com"},
            {"company": "Apple", "ticker": "AAPL", "weight": "6.5%", "domain": "apple.com"},
            {"company": "NVIDIA", "ticker": "NVDA", "weight": "6.1%", "domain": "nvidia.com"},
            {"company": "Amazon", "ticker": "AMZN", "weight": "3.5%", "domain": "amazon.com"},
            {"company": "Alphabet A", "ticker": "GOOGL", "weight": "2.2%", "domain": "abc.xyz"},
            {"company": "Meta", "ticker": "META", "weight": "2.1%", "domain": "meta.com"},
            {"company": "Alphabet C", "ticker": "GOOG", "weight": "1.9%", "domain": "abc.xyz"},
            {"company": "Berkshire Hathaway", "ticker": "BRK.B", "weight": "1.7%", "domain": "berkshirehathaway.com"},
            {"company": "Eli Lilly", "ticker": "LLY", "weight": "1.5%", "domain": "lilly.com"},
            {"company": "Broadcom", "ticker": "AVGO", "weight": "1.3%", "domain": "broadcom.com"}
        ]
    elif index_name == "nasdaq":
        return [
            {"company": "Microsoft", "ticker": "MSFT", "weight": "8.5%", "domain": "microsoft.com"},
            {"company": "Apple", "ticker": "AAPL", "weight": "8.0%", "domain": "apple.com"},
            {"company": "NVIDIA", "ticker": "NVDA", "weight": "7.5%", "domain": "nvidia.com"},
            {"company": "Amazon", "ticker": "AMZN", "weight": "5.0%", "domain": "amazon.com"},
            {"company": "Meta", "ticker": "META", "weight": "4.5%", "domain": "meta.com"},
            {"company": "Broadcom", "ticker": "AVGO", "weight": "4.0%", "domain": "broadcom.com"},
            {"company": "Alphabet A", "ticker": "GOOGL", "weight": "2.8%", "domain": "abc.xyz"},
            {"company": "Alphabet C", "ticker": "GOOG", "weight": "2.8%", "domain": "abc.xyz"},
            {"company": "Tesla", "ticker": "TSLA", "weight": "2.5%", "domain": "tesla.com"},
            {"company": "Costco", "ticker": "COST", "weight": "2.1%", "domain": "costco.com"}
        ]
    elif index_name == "dax":
        return [
            {"company": "SAP SE", "ticker": "SAP", "weight": "11.5%", "domain": "sap.com"},
            {"company": "Siemens AG", "ticker": "SIE.DE", "weight": "9.2%", "domain": "siemens.com"},
            {"company": "Allianz SE", "ticker": "ALV.DE", "weight": "7.8%", "domain": "allianz.com"},
            {"company": "Airbus SE", "ticker": "AIR.DE", "weight": "6.4%", "domain": "airbus.com"},
            {"company": "Deutsche Telekom", "ticker": "DTE.DE", "weight": "5.9%", "domain": "telekom.com"},
            {"company": "Münchener Rück", "ticker": "MUV2.DE", "weight": "4.5%", "domain": "munichre.com"},
            {"company": "Mercedes-Benz", "ticker": "MBG.DE", "weight": "3.8%", "domain": "mercedes-benz.com"},
            {"company": "BASF SE", "ticker": "BAS.DE", "weight": "3.2%", "domain": "basf.com"},
            {"company": "DHL Group", "ticker": "DHL.DE", "weight": "3.0%", "domain": "dhl.com"},
            {"company": "BMW AG", "ticker": "BMW.DE", "weight": "2.5%", "domain": "bmw.com"}
        ]
    elif index_name == "russell":
        return [
            {"company": "Super Micro", "ticker": "SMCI", "weight": "1.2%", "domain": "supermicro.com"},
            {"company": "MicroStrategy", "ticker": "MSTR", "weight": "0.9%", "domain": "microstrategy.com"},
            {"company": "Comfort Systems", "ticker": "FIX", "weight": "0.5%", "domain": "comfortsystemsusa.com"},
            {"company": "e.l.f. Beauty", "ticker": "ELF", "weight": "0.4%", "domain": "elfcosmetics.com"},
            {"company": "Light & Wonder", "ticker": "LNW", "weight": "0.4%", "domain": "lnw.com"},
            {"company": "Onto Innovation", "ticker": "ONTO", "weight": "0.4%", "domain": "ontoinnovation.com"},
            {"company": "Kinsale Capital", "ticker": "KNSL", "weight": "0.3%", "domain": "kinsalecapitalgroup.com"},
            {"company": "Simpson Mfg", "ticker": "SSD", "weight": "0.3%", "domain": "strongtie.com"},
            {"company": "Weatherford", "ticker": "WFRD", "weight": "0.3%", "domain": "weatherford.com"},
            {"company": "Rambus Inc", "ticker": "RMBS", "weight": "0.3%", "domain": "rambus.com"}
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

def get_vix_current():
    try:
        tkr = yf.Ticker('^VIX')
        hist = tkr.history(period="1d")
        if not hist.empty:
            return round(hist['Close'].iloc[-1], 2)
    except Exception as e:
        print(f"Error fetching VIX: {e}")
    return 15.0 # Fallback

def get_fed_rate():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
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
                            return {
                                "current": f"{val}%",
                                "forecast": "2.75 - 3.00% (Dec 2026)",
                                "cut_probability": "65%",
                                "hike_probability": "0%"
                            }
    except Exception as e:
        print(f"Error fetching Fed Rate: {e}")
    
    return {
        "current": "5.25 - 5.50%",
        "forecast": "2.75 - 3.00% (Dec 2026)",
        "cut_probability": "65%",
        "hike_probability": "0%"
    }

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

def get_buffett_indicator():
    try:
        gdp = get_world_bank_data('NY.GDP.MKTP.CD')
        if not gdp:
            gdp = 28750000000000
            
        ratio = 0
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get('https://www.currentmarketvaluation.com/models/buffett-indicator.php', headers=headers, timeout=10)
        from bs4 import BeautifulSoup
        import re
        soup = BeautifulSoup(r.text, 'html.parser')
        
        match = re.search(r'current Buffett Indicator value of ([\d\.]+)%', r.text, re.IGNORECASE)
        if match:
            ratio = float(match.group(1))
        
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
    if "macro_data" in macro_cache:
        return macro_cache["macro_data"]
        
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
    last_gdp = gdp_hist[-1]['value'] if gdp_hist else 27360000000000
    last_year = int(gdp_hist[-1]['year']) if gdp_hist else 2023
    
        current_year = 2026
    last_year = int(gdp_hist[-1]['year']) if gdp_hist else 2023
    projected_last_gdp = last_gdp * (1.025 ** max(0, current_year - 1 - last_year))
    
    gdp_evolution = {
        "last_year": {"year": current_year - 1, "value": projected_last_gdp},
        "this_year": {"year": current_year, "value": projected_last_gdp * 1.025},
        "next_year": {"year": current_year + 1, "value": projected_last_gdp * 1.050625}
    },
        "this_year": {"year": last_year + 1, "value": last_gdp * 1.025}, # Approx 2.5% nominal
        "next_year": {"year": last_year + 2, "value": last_gdp * 1.050}
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
    
    macro_cache["macro_data"] = data
    return data

@router.get("/market-live")
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
def get_latest_news():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get('https://query2.finance.yahoo.com/v1/finance/search?q=stock+market+news&newsCount=15', headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {"news": data.get("news", [])}
        return {"news": []}
    except Exception as e:
        print(f"Error fetching news: {e}")
        return {"news": []}
