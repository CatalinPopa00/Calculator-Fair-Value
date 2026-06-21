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

def get_index_weights(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table', class_='table')
        if not table:
            return []
        rows = table.find('tbody').find_all('tr')[:10]
        results = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                company = cols[1].text.strip()
                ticker = cols[2].text.strip()
                weight = cols[3].text.strip()
                results.append({"company": company, "ticker": ticker, "weight": weight})
        return results
    except Exception as e:
        print(f"Error fetching weights for {url}: {e}")
        return []

def get_static_etf_top10(index_name):
    if index_name == "dax":
        return [
            {"company": "SAP SE", "ticker": "SAP", "weight": "11.5%"},
            {"company": "Siemens AG", "ticker": "SIE.DE", "weight": "9.2%"},
            {"company": "Allianz SE", "ticker": "ALV.DE", "weight": "7.8%"},
            {"company": "Airbus SE", "ticker": "AIR.DE", "weight": "6.4%"},
            {"company": "Deutsche Telekom", "ticker": "DTE.DE", "weight": "5.9%"},
            {"company": "Münchener Rück", "ticker": "MUV2.DE", "weight": "4.5%"},
            {"company": "Mercedes-Benz", "ticker": "MBG.DE", "weight": "3.8%"},
            {"company": "BASF SE", "ticker": "BAS.DE", "weight": "3.2%"},
            {"company": "DHL Group", "ticker": "DHL.DE", "weight": "3.0%"},
            {"company": "BMW AG", "ticker": "BMW.DE", "weight": "2.5%"}
        ]
    elif index_name == "russell2000":
        return [
            {"company": "Super Micro Computer", "ticker": "SMCI", "weight": "1.2%"},
            {"company": "MicroStrategy", "ticker": "MSTR", "weight": "0.9%"},
            {"company": "Comfort Systems", "ticker": "FIX", "weight": "0.5%"},
            {"company": "e.l.f. Beauty", "ticker": "ELF", "weight": "0.4%"},
            {"company": "Light & Wonder", "ticker": "LNW", "weight": "0.4%"},
            {"company": "Onto Innovation", "ticker": "ONTO", "weight": "0.4%"},
            {"company": "Kinsale Capital", "ticker": "KNSL", "weight": "0.3%"},
            {"company": "Simpson Manufacturing", "ticker": "SSD", "weight": "0.3%"},
            {"company": "Weatherford Int", "ticker": "WFRD", "weight": "0.3%"},
            {"company": "Rambus Inc", "ticker": "RMBS", "weight": "0.3%"}
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
    return {
        "current": "5.25 - 5.50%",
        "forecast": "4.75 - 5.00% (Dec 2024)",
        "cut_probability": "75%",
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
    sp500 = get_index_weights('https://www.slickcharts.com/sp500')
    nasdaq = get_index_weights('https://www.slickcharts.com/nasdaq100')
    russell2000 = get_static_etf_top10("russell2000")
    dax = get_static_etf_top10("dax")
    
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
    
    gdp_evolution = {
        "last_year": {"year": last_year, "value": last_gdp},
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
            "dax": dax
        }
    }
    
    macro_cache["macro_data"] = data
    return data

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
