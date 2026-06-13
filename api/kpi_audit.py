import os
import requests
import json
import concurrent.futures
from typing import List, Dict, Any
from cachetools import TTLCache
from dotenv import load_dotenv

# Încărcăm variabilele de mediu din .env
load_dotenv()

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Cache rezultate audit (valabil 7 zile, se schimbă doar trimestrial)
audit_cache = TTLCache(maxsize=200, ttl=86400 * 7)

def _get_yahoo_earnings_news(ticker: str) -> str:
    """Fallback gratuit: Încearcă să ia știri recente despre 'Earnings' de pe Yahoo și să le parseze."""
    import yfinance as yf
    from bs4 import BeautifulSoup
    
    try:
        t = yf.Ticker(ticker)
        news = t.news
        earnings_news = []
        for n in news:
            title = n.get('title', '').lower()
            if 'earnings' in title or 'results' in title or 'quarter' in title or 'q1' in title or 'q2' in title or 'q3' in title or 'q4' in title:
                earnings_news.append(n)
                
        # Limit to 5 most recent earnings news
        earnings_news = earnings_news[:5]
        if not earnings_news:
            return ""
            
        combined_text = ""
        # Function from index.py bypass_article logic
        for item in earnings_news:
            url = item.get('link')
            if url:
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                    resp = requests.get(url, headers=headers, timeout=5)
                    soup = BeautifulSoup(resp.text, "html.parser")
                    article_body = soup.find("article") or soup.find("main") or soup.find("div", class_="caas-body")
                    if article_body:
                        text = article_body.get_text(separator=' ', strip=True)
                        combined_text += f"\n\n--- Document: {item.get('title')} ---\n{text[:5000]}" # Limiting each to 5k chars
                except:
                    pass
        return combined_text
    except Exception as e:
        print(f"Error fetching Yahoo news for {ticker}: {e}")
        return ""


def get_fmp_transcripts(ticker: str) -> str:
    """Încearcă extragerea transcrierilor oficiale dacă există API Key FMP, altfel Fallback pe Yahoo News."""
    fmp_key = os.getenv("FMP_API_KEY")
    if not fmp_key:
        print("FMP_API_KEY missing, falling back to Yahoo News Press Releases.")
        return _get_yahoo_earnings_news(ticker)
        
    try:
        # Obține lista de transcrieri disponibile
        url = f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{ticker}?apikey={fmp_key}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return _get_yahoo_earnings_news(ticker)
            
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            return _get_yahoo_earnings_news(ticker)
            
        # Păstrăm cele mai recente 4 trimestre
        recent_calls = data[:4]
        combined_text = ""
        for call in recent_calls:
            q = call.get('quarter')
            y = call.get('year')
            text = call.get('content', '')
            # Truncăm puțin din transcript ca să încapă în context (primele 10000 caractere, acolo unde managementul discută KPIs)
            combined_text += f"\n\n--- Transcript {y} Q{q} ---\n{text[:10000]}"
            
        return combined_text
    except Exception as e:
        print(f"FMP error for {ticker}: {e}")
        return _get_yahoo_earnings_news(ticker)


def run_ai_kpi_audit(ticker: str) -> Dict[str, Any]:
    ticker = ticker.upper()
    if ticker in audit_cache:
        return audit_cache[ticker]
        
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return {
            "error": True, 
            "detail": "Cheia OPENAI_API_KEY lipsește din backend. Nu putem apela AI-ul pentru audit. Te rog adaugă-o în fișierul .env."
        }
        
    if not OpenAI:
        return {"error": True, "detail": "Librăria OpenAI nu este instalată. Rulează `pip install openai`."}

    # 1. Obținem textele din rapoarte (Transcripts / Press Releases)
    raw_text = get_fmp_transcripts(ticker)
    
    if not raw_text or len(raw_text) < 500:
        return {
            "error": True,
            "detail": f"Nu am putut găsi suficiente rapoarte financiare recente sau press releases pentru {ticker}."
        }

    # 2. Apelăm OpenAI LLM
    client = OpenAI(api_key=openai_key)
    
    system_prompt = '''
Ești un analist financiar expert și un "Data Miner" de tip Hedge Fund. 
Vei primi un set de texte extrase din cele mai recente apeluri de venituri (Earnings Calls) sau comunicate de presă pentru o anumită companie.
Scopul tău este să identifici cei mai importanți 3-5 KPI (Key Performance Indicators) operaționali / calitativi specifici modelului lor de business.
EXEMPLE DE KPI BUNI: 
- Pentru Software: ARR, Net Retention Rate (NRR), Monthly Active Users (MAU), Customer Acquisition Cost.
- Pentru Auto/Hardware: Total Deliveries, Production Volume, Inventory Days.
- Pentru Retail: Same-Store Sales Growth, Loyalty Program Members.
EXEMPLE DE KPI INTERZIȘI (NU ÎI INCLUDE!): Revenue, Net Income, EPS, Profit, Gross Margin. (Aplicația le are deja!).

EXTRAGEREA VALORILOR:
Pentru fiecare KPI identificat, găsește valorile menționate în documente (în funcție de perioade - ex: Q1 2023, Q2 2023, FY 2023, etc).
Dacă nu găsești valori exacte pentru toate perioadele, pune "N/A" sau lasă valoarea pe care ai găsit-o ultima dată.

Returnează DOAR un obiect JSON valid, respectând această structură EXACTĂ:
{
  "company": "Ticker",
  "audit_summary": "Un paragraf scurt în română despre calitatea business-ului dedusă din acești indicatori.",
  "kpis": [
    {
      "name": "Numele KPI-ului (ex: Monthly Active Users)",
      "description": "Ce reprezintă și de ce e important pentru această companie (în română)",
      "values": {
        "Q3 2023": "2.5M",
        "Q4 2023": "2.8M",
        "Q1 2024": "3.1M"
      }
    }
  ]
}
'''

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Aici sunt textele pentru {ticker}:\n\n{raw_text}"}
            ],
            response_format={ "type": "json_object" },
            temperature=0.2
        )
        
        result_content = response.choices[0].message.content
        parsed_result = json.loads(result_content)
        
        # Salvare în cache
        audit_cache[ticker] = parsed_result
        return parsed_result
        
    except Exception as e:
        print(f"OpenAI Error for {ticker}: {e}")
        return {"error": True, "detail": f"Eroare la procesarea AI: {str(e)}"}
