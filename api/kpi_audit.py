import os
import requests
import json
import concurrent.futures
from typing import List, Dict, Any
from cachetools import TTLCache
try:
    from dotenv import load_dotenv
    # Încărcăm variabilele de mediu din .env (local)
    load_dotenv()
except ImportError:
    pass



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
            # Handle new yfinance nested structure vs old flat structure
            item = n.get('content', n) 
            title = item.get('title', '').lower()
            
            # Allow general news if we can't find 'earnings' so we don't fail
            earnings_news.append(item)
                
        # Limit to 5 most recent news
        earnings_news = earnings_news[:5]
        if not earnings_news:
            return ""
            
        combined_text = ""
        for item in earnings_news:
            url_dict = item.get('clickThroughUrl', {})
            url = url_dict.get('url') if isinstance(url_dict, dict) else item.get('link')
            
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

def _get_sec_10k_text(ticker: str) -> str:
    """Fetches the latest 10-K (Annual Report) from SEC EDGAR, which contains 3-5 years of historical KPIs."""
    headers = {'User-Agent': 'CalculatorFairValue calculator@fairvalue.com'}
    try:
        # 1. Get CIK for ticker
        resp = requests.get('https://www.sec.gov/files/company_tickers.json', headers=headers, timeout=5)
        data = resp.json()
        cik = None
        for k, v in data.items():
            if v['ticker'].upper() == ticker.upper():
                cik = str(v['cik_str']).zfill(10)
                break
        
        if not cik:
            return ""

        # 2. Get recent submissions
        sub_resp = requests.get(f'https://data.sec.gov/submissions/CIK{cik}.json', headers=headers, timeout=5)
        sub_data = sub_resp.json()
        recent = sub_data.get('filings', {}).get('recent', {})

        # 3. Find latest 10-K
        doc_url = None
        for i, form in enumerate(recent.get('form', [])):
            if form == '10-K':
                acc_no = recent['accessionNumber'][i].replace('-', '')
                doc = recent['primaryDocument'][i]
                doc_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{doc}'
                break

        if not doc_url:
            return ""

        # 4. Fetch 10-K HTML and extract text
        import re
        doc_resp = requests.get(doc_url, headers=headers, timeout=10)
        
        # Fast HTML stripping using regex to prevent Vercel Serverless Function timeouts (BeautifulSoup is too slow for 15MB files)
        text = re.sub(r'<[^>]+>', ' ', doc_resp.text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 10-K can be huge. The MD&A and Financials are usually in the first half. We take the first 200,000 characters.
        return f"\n\n--- SEC 10-K Report ({ticker}) ---\n" + text[:200000]

    except Exception as e:
        print(f"Error fetching SEC 10-K for {ticker}: {e}")
        return ""


def get_fmp_transcripts(ticker: str) -> str:
    """Încearcă extragerea transcrierilor oficiale dacă există API Key FMP, altfel Fallback pe Yahoo News."""
    fmp_key = os.getenv("FMP_API_KEY")
    if not fmp_key:
        print("FMP_API_KEY missing, falling back to SEC 10-K Reports.")
        sec_text = _get_sec_10k_text(ticker)
        if sec_text:
            return sec_text
        return _get_yahoo_earnings_news(ticker)
        
    try:
        # Obține lista de transcrieri disponibile
        url = f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{ticker}?apikey={fmp_key}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return _get_yahoo_earnings_news(ticker)
            
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            sec_text = _get_sec_10k_text(ticker)
            return sec_text if sec_text else _get_yahoo_earnings_news(ticker)
            
        # Păstrăm cele mai recente 20 trimestre (aprox. 5 ani istoric)
        recent_calls = data[:20]
        combined_text = ""
        for call in recent_calls:
            q = call.get('quarter')
            y = call.get('year')
            text = call.get('content', '')
            # Truncăm mai extins (20k caractere per call) ca să luăm cât mai mult context util
            combined_text += f"\n\n--- Transcript {y} Q{q} ---\n{text[:20000]}"
            
        return combined_text
    except Exception as e:
        print(f"FMP error for {ticker}: {e}")
        sec_text = _get_sec_10k_text(ticker)
        return sec_text if sec_text else _get_yahoo_earnings_news(ticker)


def run_ai_kpi_audit(ticker: str) -> Dict[str, Any]:
    ticker = ticker.upper()
    if ticker in audit_cache:
        return audit_cache[ticker]
        
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("gemini")
    if not api_key:
        return {
            "error": True, 
            "detail": "Gemini API Key is missing. Please add the 'gemini' or 'GEMINI_API_KEY' variable in the Vercel panel."
        }

    # 1. Obținem textele din rapoarte (Transcripts / Press Releases)
    raw_text = get_fmp_transcripts(ticker)
    
    if not raw_text or len(raw_text) < 500:
        return {
            "error": True,
            "detail": f"Could not find enough recent financial reports or press releases for {ticker}."
        }

    system_prompt = '''
You are an expert financial analyst and a Hedge Fund "Data Miner". 
You will receive a set of texts extracted from the most recent Earnings Calls or press releases for a specific company.
These texts may cover up to 5 years of financial history.
Your goal is to identify the top 5-10 operational / qualitative KPIs (Key Performance Indicators) specific to their business model.
EXAMPLES OF GOOD KPIs: 
- For Software: ARR, Net Retention Rate (NRR), Monthly Active Users (MAU), Customer Acquisition Cost.
- For Auto/Hardware: Total Deliveries, Production Volume, Inventory Days.
- For Retail: Same-Store Sales Growth, Loyalty Program Members.
EXAMPLES OF FORBIDDEN KPIs (DO NOT INCLUDE!): Revenue, Net Income, EPS, Profit, Gross Margin. (The app already has these!).

VALUE EXTRACTION (5-YEAR HISTORY):
For each identified KPI, find the values mentioned in the documents and track their evolution over time, over the last 5 years (by periods - e.g., FY 2020, FY 2021, FY 2022, Q1 2023, Q4 2023, etc).
Also, if you detect future estimates (Guidance), add them as future periods (e.g., FY 2025 Est.).
If you cannot find exact values for certain older historical periods, do not add them or put "N/A".

Return ONLY a valid JSON object, strictly following this EXACT structure:
{
  "company": "Ticker",
  "audit_summary": "A short paragraph summarizing the quality of the business deduced from these indicators.",
  "kpis": [
    {
      "name": "KPI Name (e.g., Monthly Active Users)",
      "description": "What it represents and why it is important for this company.",
      "values": {
        "Q3 2023": "2.5M",
        "Q4 2023": "2.8M",
        "Q1 2024": "3.1M"
      }
    }
  ]
}
'''

    # 2. Apelăm API-ul Gemini nativ prin requests (fără SDK extern pentru a evita probleme de instalare pe Vercel)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [{
            "parts": [{"text": f"Aici sunt textele pentru {ticker}:\n\n{raw_text}"}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=55)

        if resp.status_code != 200:
            error_msg = resp.text
            try:
                error_data = resp.json()
                if "error" in error_data and "message" in error_data["error"]:
                    error_msg = error_data["error"]["message"]
            except:
                pass
            return {"error": True, "detail": f"Gemini API Error: {error_msg}"}
            
        data = resp.json()

        if "candidates" not in data or not data["candidates"]:
            return {"error": True, "detail": "Gemini returned an empty response."}
            
        result_content = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed_result = json.loads(result_content)

        # Salvare în cache
        audit_cache[ticker] = parsed_result
        return parsed_result

    except json.JSONDecodeError:
        return {"error": True, "detail": "Gemini nu a returnat un format JSON valid. Încearcă din nou."}
    except Exception as e:
        print(f"Gemini API Error for {ticker}: {e}")
        return {"error": True, "detail": f"Eroare la procesarea AI: {str(e)}"}
