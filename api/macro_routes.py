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
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
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
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
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
            gdp = 28750000000000 # Fallback 2024 approx
            
        ratio = 0
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        r = requests.get('https://www.currentmarketvaluation.com/models/buffett-indicator.php', headers=headers, timeout=10)
        from bs4 import BeautifulSoup
        import re
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Look for "current Buffett Indicator value of 219%"
        match = re.search(r'current Buffett Indicator value of ([\d\.]+)%', r.text, re.IGNORECASE)
        if match:
            ratio = float(match.group(1))
        
        if ratio == 0:
            # Fallback if text changes
            return {"ratio": 0, "market_cap_trillions": 0, "gdp_trillions": round(gdp / 1_000_000_000_000, 2)}
        
        # Calculate implied Market Cap
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

@router.get("/news")
def get_latest_news():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        r = requests.get('https://query2.finance.yahoo.com/v1/finance/search?q=stock+market+news&newsCount=15', headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {"news": data.get("news", [])}
        return {"news": []}
    except Exception as e:
        print(f"Error fetching news: {e}")
        return {"news": []}
