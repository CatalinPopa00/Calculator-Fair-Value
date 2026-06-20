from fastapi import APIRouter
from cachetools import TTLCache
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
import requests
import json
import yfinance as yf

router = APIRouter()

# Cache macro data for 24 hours
macro_cache = TTLCache(maxsize=10, ttl=86400)

def get_fear_and_greed():
    try:
        r = cffi_requests.get('https://production.dataviz.cnn.io/index/fearandgreed/graphdata', impersonate='chrome110', timeout=10)
        data = r.json()
        score = data.get('fear_and_greed', {}).get('score', 50)
        rating = data.get('fear_and_greed', {}).get('rating', 'neutral')
        return {"score": round(score), "rating": rating}
    except Exception as e:
        print(f"Error fetching Fear & Greed: {e}")
        return {"score": 50, "rating": "neutral (error)"}

def get_index_weights(url):
    try:
        r = cffi_requests.get(url, impersonate='chrome110', timeout=10)
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

def get_world_bank_data(indicator):
    try:
        r = requests.get(f'http://api.worldbank.org/v2/country/US/indicator/{indicator}?format=json', timeout=10)
        data = r.json()
        if len(data) > 1 and isinstance(data[1], list):
            for item in data[1]:
                if item.get('value') is not None:
                    return item['value']
    except Exception as e:
        print(f"Error fetching World Bank {indicator}: {e}")
    return None

def get_buffett_indicator():
    try:
        # Get US GDP from World Bank
        gdp = get_world_bank_data('NY.GDP.MKTP.CD')
        if not gdp:
            gdp = 27360000000000 # Fallback 2023 approx
            
        # Get Wilshire 5000 Market Cap
        w5000 = yf.Ticker('^W5000')
        hist = w5000.history(period="1d")
        if hist.empty:
            return {"ratio": 0, "market_cap": 0, "gdp": gdp}
        
        index_val = hist['Close'].iloc[-1]
        # The Wilshire 5000 index value represents market cap in billions.
        # e.g. index value 50,000 means $50 Trillion market cap approx
        market_cap = index_val * 1_000_000_000
        
        ratio = (market_cap / gdp) * 100
        
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
    buffett = get_buffett_indicator()
    
    inflation = get_world_bank_data('FP.CPI.TOTL.ZG')
    unemployment = get_world_bank_data('SL.UEM.TOTL.ZS')
    
    data = {
        "fear_greed": fear_greed,
        "sp500_top10": sp500,
        "nasdaq_top10": nasdaq,
        "buffett_indicator": buffett,
        "inflation_pct": round(inflation, 2) if inflation else 0,
        "unemployment_pct": round(unemployment, 2) if unemployment else 0
    }
    
    macro_cache["macro_data"] = data
    return data
