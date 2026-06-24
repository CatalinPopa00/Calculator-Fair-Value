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

try:
    from utils.kv import kv_get, kv_set
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    import os; sys.path.append(os.path.dirname(os.path.dirname(__file__))); from utils.kv import kv_get, kv_set

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

        # 3. Find up to 5 latest 10-Ks and 3 latest 10-Qs to get both historical and current year data
        doc_urls = []
        k_count = 0
        q_count = 0
        most_recent_k_year = None
        
        def extract_filings(filings_obj):
            nonlocal k_count, q_count, most_recent_k_year
            for i, form in enumerate(filings_obj.get('form', [])):
                year = filings_obj['reportDate'][i][:4]
                if form == '10-K' and k_count < 5:
                    if most_recent_k_year is None:
                        most_recent_k_year = year
                    acc_no = filings_obj['accessionNumber'][i].replace('-', '')
                    doc = filings_obj['primaryDocument'][i]
                    doc_urls.append(('10-K', year, f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{doc}'))
                    k_count += 1
                elif form == '10-Q' and q_count < 3:
                    # Only accept 10-Qs if they are for a year strictly newer than the most recent 10-K year
                    if most_recent_k_year is not None and year <= most_recent_k_year:
                        continue
                    acc_no = filings_obj['accessionNumber'][i].replace('-', '')
                    doc = filings_obj['primaryDocument'][i]
                    # Format as Year Qx. SEC reportDate is YYYY-MM-DD.
                    # Simplistic quarter mapping based on month.
                    month = int(filings_obj['reportDate'][i][5:7])
                    quarter = 'Q1' if month <= 3 else ('Q2' if month <= 6 else ('Q3' if month <= 9 else 'Q4'))
                    year_q = f"{year} {quarter}"
                    doc_urls.append(('10-Q', year_q, f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{doc}'))
                    q_count += 1
                    
                if k_count >= 5 and q_count >= 4:
                    break
                        
        extract_filings(recent)
        
        if k_count < 5 or q_count < 4:
            for file_info in sub_data.get('filings', {}).get('files', []):
                try:
                    older_url = f"https://data.sec.gov/submissions/{file_info['name']}"
                    older_resp = requests.get(older_url, headers=headers, timeout=5)
                    older_data = older_resp.json()
                    extract_filings(older_data)
                    if k_count >= 5 and q_count >= 4:
                        break
                except:
                    pass

        if not doc_urls:
            return ""

        # 4. Fetch HTML and extract text
        import re
        import html
        combined_text = f"\n\n--- SEC Reports for {ticker} ---\n"
        for form_type, date_str, doc_url in doc_urls:
            try:
                doc_resp = requests.get(doc_url, headers=headers, timeout=10)
                # Unescape HTML entities (like &#160; for spaces) before stripping tags!
                text = html.unescape(doc_resp.text)
                # Fast HTML stripping using regex to prevent Vercel Serverless Function timeouts
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                
                if form_type == '10-K':
                    # Jump directly to Item 7 (MD&A)
                    matches = list(re.finditer(r'(?i)Item\s*7[\.\:]?\s*Management', text))
                    valid_matches = [m for m in matches if m.start() > 100000]
                    if valid_matches:
                        idx = valid_matches[0].start()
                    elif matches:
                        idx = matches[-1].start()
                    else:
                        idx = 0
                        
                    # Find end boundary Item 8
                    matches_end = list(re.finditer(r'(?i)Item\s*8[\.\:]?\s*Financial', text))
                    valid_end = [m for m in matches_end if m.start() > idx]
                    if valid_end and valid_end[0].start() - idx < 15000:
                        report_text = text[idx:valid_end[0].start()]
                    else:
                        report_text = text[idx:idx+15000]
                        
                    combined_text += f"\n\n[Year {date_str} 10-K]\n" + report_text
                else:
                    # Jump directly to Item 2 (MD&A for 10-Q)
                    matches = list(re.finditer(r'(?i)Item\s*2[\.\:]?\s*Management', text))
                    valid_matches = [m for m in matches if m.start() > 30000]
                    if valid_matches:
                        idx = valid_matches[0].start()
                    elif matches:
                        idx = matches[-1].start()
                    else:
                        idx = 0
                        
                    # Find end boundary Item 3
                    matches_end = list(re.finditer(r'(?i)Item\s*3[\.\:]?\s*Quantitative', text))
                    valid_end = [m for m in matches_end if m.start() > idx]
                    if valid_end and valid_end[0].start() - idx < 10000:
                        report_text = text[idx:valid_end[0].start()]
                    else:
                        report_text = text[idx:idx+10000]
                        
                    combined_text += f"\n\n[Year {date_str} 10-Q]\n" + report_text
            except:
                pass

        if not combined_text:
            return ""

        # Dynamically tell the AI what periods are available based on what we fetched
        available_periods_str = ", ".join([f"{u[1]} ({u[0]})" for u in doc_urls])

        system_prompt = f"""
You are a top-tier Wall Street Financial Analyst AI.
Your objective is to read the provided SEC 10-K and 10-Q excerpts for a company and extract their historical Key Performance Indicators (KPIs).

AVAILABLE PERIODS IN TEXT: {available_periods_str}

YOUR MISSION:
Identify up to 8 of the MOST CRITICAL, COMPANY-SPECIFIC, OPERATIONAL Key Performance Indicators (KPIs).
- Focus ONLY on user/customer metrics (e.g. Monthly Active Users, Subscriptions), volume metrics (e.g. Total Payment Volume, Deliveries), or operational financial metrics deeply specific to their business model (e.g. Annualized Recurring Revenue (ARR), Gross Merchandise Volume (GMV)).
- DO NOT extract generic accounting metrics (e.g. Net Income, Gross Profit, Total Assets, EPS). We already have those.
- Only extract KPIs that have numerical data available across the years.

CRITICAL EXTRACTION RULE:
You MUST extract the value ONLY for the specific periods provided in the text tags. 
Do NOT invent keys that are not present in the text tags. 
If a value for a specific period is completely absent from the provided text, you may briefly check your internal knowledge to fill in the gaps. Only use "N/A" if the data is truly impossible to find.

FORMATTING RULES:
Format the keys EXACTLY matching the period string from the tags (e.g., "FY 2025" for 10-K, or "FY 2025 Q1" for 10-Q).
Ensure exact numbers are extracted if explicitly stated. Format numbers cleanly (e.g. "1.2 Billion", "34.5%", "450 Million"). Do not write raw large numbers.
Make sure the description is concise (max 2 sentences) and professional.

Return ONLY a valid JSON matching this exact structure:
{{
  "kpis": [
    {{
      "name": "Annualized Recurring Revenue (ARR)",
      "description": "Represents the annualized value of all active subscription contracts.",
      "values": {{
        "FY 2021": "1.5 Billion",
        "FY 2022": "2.0 Billion"
      }}
    }}
  ]
}}
"""

        # Choose the Gemini models that are extremely fast to avoid Vercel 60s timeout
        if not os.getenv("GEMINI_API_KEY") and not os.getenv("gemini"):
            return combined_text

        return combined_text

    except Exception as e:
        print(f"Error fetching SEC 10-K for {ticker}: {e}")
        return ""


# Cache for raw transcripts (7 days)
transcripts_cache = TTLCache(maxsize=100, ttl=86400 * 7)

def get_fmp_transcripts(ticker: str) -> str:
    """Încearcă extragerea transcrierilor oficiale dacă există API Key FMP, altfel Fallback pe Yahoo News."""
    ticker = ticker.upper()
    if ticker in transcripts_cache:
        return transcripts_cache[ticker]

    fmp_key = os.getenv("FMP_API_KEY")
    if not fmp_key:
        print("FMP_API_KEY missing, falling back to SEC 10-K Reports.")
        sec_text = _get_sec_10k_text(ticker)
        yahoo_text = _get_yahoo_earnings_news(ticker)
        res = sec_text + "\n\n" + yahoo_text
        transcripts_cache[ticker] = res
        return res
        
    try:
        # Obține lista de transcrieri disponibile
        url = f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{ticker}?apikey={fmp_key}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        if not data or not isinstance(data, list):
            print("No FMP transcripts found, falling back to SEC.")
            sec_text = _get_sec_10k_text(ticker)
            yahoo_text = _get_yahoo_earnings_news(ticker)
            res = sec_text + "\n\n" + yahoo_text
            transcripts_cache[ticker] = res
            return res
            
        # Păstrăm cele mai recente 20 trimestre (aprox. 5 ani istoric)
        recent_calls = data[:20]
        combined_transcripts = ""
        
        for call in recent_calls:
            q = call.get('quarter')
            y = call.get('year')
            content = call.get('content', '')
            # Scurtăm conținutul agresiv pentru a evita token limits (primele 4.000 caractere, aprox 1k tokens)
            combined_transcripts += f"\n\n--- Earnings Call Q{q} {y} ---\n{content[:4000]}"
            
        if not combined_transcripts.strip():
            sec_text = _get_sec_10k_text(ticker)
            yahoo_text = _get_yahoo_earnings_news(ticker)
            res = sec_text + "\n\n" + yahoo_text
            transcripts_cache[ticker] = res
            return res
            
        transcripts_cache[ticker] = combined_transcripts
        return combined_transcripts
        
    except Exception as e:
        print(f"Error fetching FMP transcripts for {ticker}: {e}")
        sec_text = _get_sec_10k_text(ticker)
        yahoo_text = _get_yahoo_earnings_news(ticker)
        res = sec_text + "\n\n" + yahoo_text
        transcripts_cache[ticker] = res
        return res

def _perform_web_search(search_engine_query: str, llm_research_prompt: str) -> tuple[str, str]:
    import os
    import requests
    import urllib.parse
    import time
    
    tavily_key = os.environ.get("TAVILY_API_KEY")
    brave_key = os.environ.get("BRAVE_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("gemini")
    
    search_success = False
    live_research_data = ""
    research_error = ""

    # 1. TAVILY API (Priority 1)
    if not search_success and tavily_key:
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": tavily_key,
                    "query": search_engine_query,
                    "search_depth": "advanced",
                    "include_answer": True,
                    "max_results": 5
                },
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                live_research_data = data.get("answer", "") + "\n\nSources:\n" + "\n".join([f"- {r.get('url')}: {r.get('content')}" for r in data.get("results", [])])
                research_error = ""
                search_success = True
            else:
                research_error += f"Tavily Error {resp.status_code}: {resp.text[:100]} | "
        except Exception as e:
            research_error += f"Tavily Exception: {str(e)} | "

    # 2. BRAVE SEARCH API (Priority 2)
    if not search_success and brave_key:
        try:
            resp = requests.get(
                f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(search_engine_query)}",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": brave_key
                },
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("web", {}).get("results", [])
                live_research_data = "Brave Search Results:\n" + "\n".join([f"- {r.get('title')}: {r.get('description')}" for r in results[:5]])
                research_error = ""
                search_success = True
            else:
                research_error += f"Brave Error {resp.status_code}: {resp.text[:100]} | "
        except Exception as e:
            research_error += f"Brave Exception: {str(e)} | "

    # 3. GEMINI 2.0 FLASH (Priority 3)
    if not search_success and gemini_key:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                gemini_payload = {
                    "contents": [{"role": "user", "parts": [{"text": llm_research_prompt}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
                    "tools": [{"google_search": {}}]
                }
                resp = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                    headers={"Content-Type": "application/json"},
                    json=gemini_payload,
                    timeout=15
                )
                if resp.status_code == 200:
                    live_research_data = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    research_error = ""
                    search_success = True
                    break
                elif resp.status_code == 429:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        research_error += "Gemini Error: 429 Rate Limit | "
                        break
                else:
                    research_error += f"Gemini Error {resp.status_code}: {resp.text[:100]} | "
                    break
            except Exception as e:
                research_error += f"Gemini Exception: {str(e)} | "
                break

    # 4. DUCKDUCKGO SEARCH (Priority 4 - Ultimate Free Fallback)
    if not search_success:
        try:
            from duckduckgo_search import DDGS
            results = DDGS().text(search_engine_query, max_results=4)
            if results:
                live_research_data = "DuckDuckGo Search Results:\n" + "\n".join([f"- {r.get('title')} ({r.get('href')}): {r.get('body')}" for r in results])
                research_error = ""
                search_success = True
            else:
                research_error += "DuckDuckGo Error: No results found | "
        except Exception as e:
            research_error += f"DuckDuckGo Exception: {str(e)} | "

    if not search_success:
        print(f"All Search Providers Failed: {research_error}")
        
    return live_research_data, research_error

def run_ai_kpi_audit(ticker: str, force_refresh: bool = False) -> Dict[str, Any]:
    ticker = ticker.upper()
    
    if not force_refresh and ticker in audit_cache:
        return audit_cache[ticker]
        
    redis_key = f"audit:{ticker}"
    if not force_refresh:
        cached_data = kv_get(redis_key)
        if cached_data:
            try:
                data = json.loads(cached_data) if isinstance(cached_data, (str, bytes)) else cached_data
                audit_cache[ticker] = data
                return data
            except:
                pass

    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except:
        pass

    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("gemini")
    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("Groq")

    # Auto-detect if user accidentally put an OpenAI key in a Gemini variable
    if gemini_key and gemini_key.startswith("sk-"):
        if not openai_key:
            openai_key = gemini_key
        gemini_key = None

    if not openai_key and not gemini_key and not groq_key:
        return {
            "error": True, 
            "detail": "No API Key found. Please add 'GROQ_API_KEY', 'OPENAI_API_KEY' or 'GEMINI_API_KEY' in the Vercel panel."
        }

    # 1. Obținem textele din rapoarte (Transcripts / Press Releases)
    raw_text = get_fmp_transcripts(ticker)
    
    # Strictly limit raw_text to max 14,000 characters (~3,500 tokens)
    # This prevents free-tier API daily limits (like Groq's 100k TPD limit) from being exhausted instantly
    if raw_text and len(raw_text) > 14000:
        raw_text = raw_text[:14000]

    # If the text is small (e.g. < 5000 chars, meaning SEC/FMP failed and we only got Yahoo News), trigger web search
    if not raw_text or len(raw_text) < 5000:
        search_query = f"{ticker} stock key performance indicators revenue by division order backlog FY2022 FY2023 FY2024"
        llm_prompt = f"Perform a comprehensive web search to find the historical Key Performance Indicators (KPIs) for {ticker} from FY2022 to the present. Focus on order backlog, revenue by division/segment, and core operational metrics. Return the exact numerical values found for each year."
        live_research_data, research_error = _perform_web_search(search_query, llm_prompt)
        
        if live_research_data:
            raw_text = raw_text + f"\n\n--- Web Search Results for KPIs ---\n{live_research_data}"

    if not raw_text or len(raw_text) < 500:
        return {
            "error": True,
            "detail": f"Could not find enough recent financial reports, press releases, or search results for {ticker}."
        }

    system_prompt = '''
You are a top-tier Wall Street Financial Analyst & Data Extraction AI. 
You will receive a set of texts extracted from the most recent Earnings Calls or SEC reports for a specific company.
These texts cover up to 5 years of financial history.

YOUR MISSION:
Identify AT LEAST 5 and up to 8 of the MOST CRITICAL, CORE COMPANY-SPECIFIC Key Performance Indicators (KPIs) for this company. You MUST use your internal knowledge to identify the remaining critical operational KPIs if the text does not contain enough. Think like a hedge fund analyst breaking down the core drivers of the business.

CRITICAL KPI SELECTION RULES (STRICTLY ENFORCED UNDER PENALTY OF FAILURE):
1. Focus on OFFICIAL REPORTING SEGMENTS & BACKLOG: You MUST include "Order Backlog" if applicable to the company. You MUST use the standard, official names for the company's reporting segments (e.g. for Adobe: "Digital Media Revenue", "Digital Experience Revenue"; for Rheinmetall: "Vehicle Systems", "Weapon and Ammunition"). Do NOT use hyper-specific phrasing from a single paragraph. Using standard names ensures you can retrieve historical data accurately.
2. AVOID NICHE METRICS: Do NOT extract data about minor acquisitions, tiny side-businesses, or one-off costs. Focus on what drives the MAIN revenue streams.
3. ABSOLUTE BAN ON GENERIC FINANCIAL METRICS: You are STRICTLY FORBIDDEN from extracting generic accounting or generic headcount items! BANNED METRICS: EBITDA, EBITDA Margin, Earnings Per Share, EPS, Net Income, Total Revenue, Gross Margin, Cash Flow, Operating Income, Profit, Debt, Assets, Opex, R&D Expenses, CapEx, Headcount/Number of employees. 

VALUE EXTRACTION (HISTORY SINCE FY 2021 + RECENT QUARTERS):
For each identified KPI, track its evolution starting from FY 2021 up to the most recently completed fiscal year.
ADDITIONALLY, extract the available individual quarterly data (e.g., Q1, Q2) for the CURRENT unfinished fiscal year ONLY IF THEY HAVE ALREADY BEEN REPORTED.
Format the keys EXACTLY as "FY [Year]" or "FY [Year] Q[X]". Format numbers cleanly (e.g. "1.2 Billion", "34.5%", "450 Million"). 

CRITICAL EXTRACTION RULE - HYBRID APPROACH: 
- For ALL PAST FULLY COMPLETED FISCAL YEARS (e.g., FY 2021 to the last completed year), you MUST use your internal knowledge base to fill in the exact historical numbers for the identified KPIs if they are not explicitly present in the text. You are REQUIRED to fill the history for FY 2021, FY 2022, FY 2023, and FY 2024. Do not leave historical years blank.
- For the CURRENT ONGOING FISCAL YEAR and UNFINISHED QUARTERS (e.g., the current reporting year), you MUST extract the numerical values ONLY if they are explicitly stated in the provided text. STRICT BAN ON HALLUCINATION for recent and future quarters! Do NOT invent values and do NOT add quarters that have not been officially reported yet!

Return ONLY a valid JSON object, strictly following this EXACT structure:
{
  "company": "Ticker",
  "audit_summary": "A short paragraph summarizing the quality of the business deduced from these indicators.",
  "kpis": [
    {
      "name": "KPI Name (e.g., Monthly Active Users)",
      "description": "What it represents and why it is important for this company.",
      "values": {
        "FY 2021": "1.5M",
        "FY 2022": "2.0M"
      }
    }
  ]
}
'''

    try:
        import time
        result_content = None
        all_errors = []
        start_time = time.time()
        MAX_TOTAL_TIME = 55  # Leave 5s buffer before Vercel's 60s timeout

        def time_left():
            return MAX_TOTAL_TIME - (time.time() - start_time)

        # Try Groq First if available (Free and Fast)
        if groq_key and time_left() > 5:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {groq_key}"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Aici sunt textele pentru {ticker}:\n\n{raw_text}"}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
            for model_idx, groq_model in enumerate(groq_models):
                if result_content:
                    break
                payload["model"] = groq_model
                for attempt in range(3):
                    if time_left() < 5:
                        break
                    try:
                        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=min(20, time_left() - 2))
                        if resp.status_code == 200:
                            data = resp.json()
                            result_content = data["choices"][0]["message"]["content"]
                            break
                        elif resp.status_code == 429:
                            # Log the actual error body for debugging
                            error_detail = resp.text[:300]
                            try:
                                error_detail = resp.json().get("error", {}).get("message", resp.text[:300])
                            except:
                                pass
                            print(f"Groq 429 for {groq_model}. Attempt {attempt+1}/3. Detail: {error_detail}")
                            if attempt < 2 and time_left() > 10:
                                time.sleep(min(3 * (2 ** attempt), time_left() - 5))
                                continue
                            else:
                                all_errors.append(f"Groq {groq_model}: 429 - {error_detail[:100]}")
                                break
                        else:
                            error_msg = resp.text
                            try:
                                error_msg = resp.json().get("error", {}).get("message", resp.text)
                            except:
                                pass
                            all_errors.append(f"Groq Error: {error_msg}")
                            break
                    except Exception as e:
                        all_errors.append(f"Groq Timeout/Error: {str(e)}")
                        break

        # Try OpenAI if Groq failed or wasn't configured
        if not result_content and openai_key and time_left() > 5:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai_key}"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Aici sunt textele pentru {ticker}:\n\n{raw_text}"}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            try:
                resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=min(25, time_left() - 2))
                if resp.status_code == 200:
                    data = resp.json()
                    result_content = data["choices"][0]["message"]["content"]
                else:
                    error_msg = resp.text
                    try:
                        error_msg = resp.json().get("error", {}).get("message", resp.text)
                    except:
                        pass
                    all_errors.append(f"OpenAI Error: {error_msg}")
            except Exception as e:
                all_errors.append(f"OpenAI Timeout/Error: {str(e)}")

        # Try Gemini if all above failed
        if not result_content and gemini_key and time_left() > 5:
            models_to_try = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.5-flash-lite"
            ]
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [{"text": f"{system_prompt}\n\nAici sunt textele pentru {ticker}:\n\n{raw_text}"}]
                }],
                "generationConfig": {"temperature": 0.2}
            }
            for idx, model in enumerate(models_to_try):
                if result_content or time_left() < 5:
                    break
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"

                for attempt in range(3):
                    if time_left() < 5:
                        break
                    try:
                        resp = requests.post(url, headers=headers, json=payload, timeout=min(20, time_left() - 2))
                        if resp.status_code == 200:
                            data = resp.json()
                            try:
                                if "candidates" in data and data["candidates"]:
                                    result_content = data["candidates"][0]["content"]["parts"][0]["text"]
                                    break
                            except (KeyError, IndexError):
                                all_errors.append(f"Gemini {model} blocked or missing text parts")
                                break
                        elif resp.status_code in (429, 503):
                            print(f"Gemini {resp.status_code} for {model}. Attempt {attempt+1}/3.")
                            if attempt < 2 and time_left() > 8:
                                time.sleep(min(3 * (2 ** attempt), time_left() - 5))
                                continue
                            else:
                                all_errors.append(f"Gemini {model}: {resp.status_code} Rate Limit")
                                break
                        else:
                            error_msg = resp.text
                            try:
                                err_data = resp.json()
                                if "error" in err_data and "message" in err_data["error"]:
                                    error_msg = err_data["error"]["message"]
                            except:
                                pass
                            all_errors.append(f"Gemini {model}: {error_msg}")
                            break
                    except Exception as e:
                        all_errors.append(f"Gemini {model} Timeout/Error: {str(e)}")
                        break

        if not result_content:
            return {"error": True, "detail": "AI API Error: " + " | ".join(all_errors)}

        # Remove potential markdown formatting
        if result_content.strip().startswith("```json"):
            result_content = result_content.strip()[7:]
        if result_content.strip().startswith("```"):
            result_content = result_content.strip()[3:]
        if result_content.strip().endswith("```"):
            result_content = result_content.strip()[:-3]
            
        parsed_result = json.loads(result_content.strip())

        # Salvare în cache
        audit_cache[ticker] = parsed_result
        kv_set(redis_key, json.dumps(parsed_result), ex=2592000) # 30 days
        return parsed_result

    except json.JSONDecodeError:
        return {"error": True, "detail": "AI nu a returnat un format JSON valid. Încearcă din nou."}
    except Exception as e:
        print(f"AI API Error for {ticker}: {e}")
        return {"error": True, "detail": f"Eroare la procesarea AI: {str(e)}"}

def run_ai_chat(ticker: str, context: dict, history: list, message: str) -> str:
    """Handles conversational queries from the frontend Chat Widget."""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except:
        pass

    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("gemini")
    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("Groq")

    # Auto-detect if user accidentally put an OpenAI key in a Gemini variable
    if gemini_key and gemini_key.startswith("sk-"):
        if not openai_key:
            openai_key = gemini_key
        gemini_key = None

    if not openai_key and not gemini_key and not groq_key:
        return "Eroare: Niciun API Key configurat (Groq, OpenAI sau Gemini). Adaugă GROQ_API_KEY, OPENAI_API_KEY sau GEMINI_API_KEY în Vercel Environment Variables."

    import datetime
    current_date = datetime.date.today().strftime('%B %d, %Y')
    
    # Build base system prompt (without live research yet)
    base_system_prompt = f"""
You are "Babi AI", an elite, highly critical Wall Street Financial Analyst integrated into the 'Babi Calculator-inatorul' dashboard.
TODAY'S DATE IS: {current_date}. You MUST ALWAYS act like we are in the year {datetime.date.today().year}. 
NEVER say you don't have access to real-time data or that your knowledge is cut off.
The user is currently analyzing the ticker: {ticker}.
Here is the real-time context of the company you MUST use to answer their questions:
- Current Price: {context.get('price')}
- Estimated Fair Value: {context.get('fairValue')}
- Margin of Safety: {context.get('marginOfSafety')}
- Recent News Headlines: {context.get('news', 'N/A')}
- AI KPI Audit Summary: {context.get('kpiSummary', 'N/A')}
- Risk Red Flags: {context.get('redFlags', 'N/A')}
- Business Summary: {context.get('businessSummary', 'N/A')}
- Yahoo Finance & Wall Street Analyst Estimates: {context.get('estimates', 'N/A')}
- Yahoo Finance Data (EPS, Revenue, etc): {context.get('financials', 'N/A')}
- SEC Reports & Earnings Transcripts:
{get_fmp_transcripts(ticker)[:4000]}
"""

    instructions = """
Instructions:
1. **Conversational Continuity & Deep Competence:** Actively track the flow of the conversation. Be clear, concise, and direct. Find solutions, do not make excuses. Do not write excessively long essays unless strictly necessary. Provide high-impact financial analysis.
2. **Current Date Awareness:** You are living in the present day. Do NOT say you are from 2021 or 2022. Do NOT say "As an AI...". Answer the user's questions confidently.
3. **Quote Formatting Rule:** When you provide a direct quote, DO NOT use quotation marks ("" or '') and DO NOT use italics. Instead, put a colon (:) at the end of your introductory sentence, write the quote on a completely new line, and leave a blank empty line before and after the quote to separate it from the rest of the text.
4. **Earnings & Revenue Estimates & CAGR:** Our local `Estimates` context only has data for the next 2 years. If the user asks for multi-year estimates (e.g. 3, 4, or 5 years) from Nasdaq, YOU MUST ACTIVELY USE THE SEARCH TOOL to search '[ticker] earnings estimates 2026 2027 2028' (do NOT restrict the search to Nasdaq, let the search engine find data from SeekingAlpha, WallStreetZen etc) to fetch the multi-year EPS and Revenue estimates directly from the web! Also, when calculating the Compound Annual Growth Rate (CAGR) for these estimates, you MUST ALWAYS calculate it starting from the LAST FULLY REPORTED YEAR (the most recently completed historical year), NOT starting from an estimated year like 2026.
5. **Live Research Integration:** If LIVE RESEARCH DATA is provided above, use it extensively to answer the user's question with facts from TODAY.
6. **KNOWLEDGE CUTOFF OVERRIDE & SEC REPORTS SEARCH:** You MUST IGNORE your internal 'Cutting Knowledge Date'. If the user asks for data from a specific past year (e.g., 2023 SEC 10-K, 2023 Revenue) or specific historical earnings transcripts that are NOT in the local context, YOU MUST USE YOUR SEARCH TOOL (if available) to search the web (e.g. 'MSFT 2023 10-K' or 'MSFT Q3 2023 transcript') and extract the exact numbers! NEVER say you don't have access to past reports.
7. **INTERNET SEARCH DIAGNOSTIC:** If the LIVE RESEARCH DATA block says [FAILED], you MUST reply EXACTLY with this: "Eroare internă la modulul de căutare web: [Include the Reason provided in the LIVE RESEARCH DATA block]. Din acest motiv, nu am acces la date de pe internet în acest moment."
8. **Tone & Language:** Speak natively and naturally in Romanian. Be highly confident, professional, concise, and solution-oriented.
"""

    live_research_data, research_error = _perform_web_search(search_engine_query, llm_research_prompt)

    # Build Final System Prompt
    system_prompt = base_system_prompt
    if live_research_data:
        system_prompt += f"- LIVE RESEARCH DATA (from your AI Assistant): {live_research_data}\n"
    elif research_error:
        system_prompt += f"- LIVE RESEARCH DATA: [FAILED] Reason: {research_error}\n"
    system_prompt += instructions

    # Prepare message history (limit to last 6 interactions to save tokens)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-6:]:
        api_role = "assistant" if msg["role"] == "ai" else "user"
        messages.append({"role": api_role, "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    # MULTI-MODEL PIPELINE: Phase 2 (Gemini Primary with Native Search)
    # We prioritize Gemini because it has the google_search tool native, which solves the user's issue with "AI doesn't know how to search".
    if gemini_key:
        try:
            gemini_messages = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in messages if m["role"] != "system"]
            gemini_payload = {
                "contents": gemini_messages,
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
                "tools": [{"google_search": {}}]
            }

            chat_models_to_try = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.5-flash-lite"
            ]

            import time
            for idx, model in enumerate(chat_models_to_try):
                if result_content:
                    break
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        resp = requests.post(url, headers={"Content-Type": "application/json"}, json=gemini_payload, timeout=12.0)

                        if resp.status_code == 400 and "tools" in gemini_payload:
                            payload_no_tools = gemini_payload.copy()
                            del payload_no_tools["tools"]
                            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload_no_tools, timeout=8.0)

                        if resp.status_code == 200:
                            data = resp.json()
                            try:
                                result_content = data["candidates"][0]["content"]["parts"][0]["text"]
                                break
                            except (KeyError, IndexError):
                                all_errors.append(f"Gemini {model} Chat missing text parts")
                                break
                        elif resp.status_code == 429:
                            if attempt < max_retries - 1:
                                time.sleep(2 ** attempt)
                                continue
                            else:
                                all_errors.append(f"Gemini {model} Chat Rate Limit")
                                if idx < len(chat_models_to_try) - 1:
                                    time.sleep(2)
                        else:
                            error_msg = resp.text[:200]
                            print(f"Gemini Chat Error ({model}): {error_msg}")
                            all_errors.append(f"Gemini {model}({resp.status_code}): {error_msg}")
                            break
                    except Exception as e:
                        print(f"Gemini Chat Exception ({model}): {e}")
                        all_errors.append(f"Gemini {model}: {str(e)}")
                        break

                if result_content:
                    break
        except Exception as e:
            print(f"Gemini Chat Main Exception: {e}")
            all_errors.append(f"Gemini: {str(e)}")

    # Fallback 1: Groq Analyst
    if not result_content and groq_key:
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"},
                    json={"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.5, "max_tokens": 1024},
                    timeout=30
                )
                if resp.status_code == 200:
                    choice = resp.json().get("choices", [{}])[0]
                    result_content = choice.get("message", {}).get("content", "")
                    
                    if choice.get("finish_reason") == "length":
                        print(f"Groq truncated message mid-sentence (hit TPM limits).")
                    break
                elif resp.status_code == 429:
                    print(f"Groq Rate Limit (429) hit in Chat. Attempt {attempt+1}/{max_retries}.")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        error_msg = "429 Rate Limit Exhausted"
                        print(f"Groq Chat Error (status {resp.status_code}): {error_msg}")
                        all_errors.append(f"Groq({resp.status_code}): {error_msg}")
                        break
                else:
                    error_msg = resp.text[:200]
                    print(f"Groq Chat Error (status {resp.status_code}): {error_msg}")
                    all_errors.append(f"Groq({resp.status_code}): {error_msg}")
                    break
            except Exception as e:
                print(f"Groq Chat Exception: {e}")
                all_errors.append(f"Groq: {str(e)}")
                break

    # Fallback 2: OpenAI
    if not result_content and openai_key:
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"},
                json={"model": "gpt-4o-mini", "messages": messages, "temperature": 0.5},
                timeout=30
            )
            if resp.status_code == 200:
                result_content = resp.json()["choices"][0]["message"]["content"]
            else:
                error_msg = resp.text[:200]
                print(f"OpenAI Chat Error (status {resp.status_code}): {error_msg}")
                all_errors.append(f"OpenAI({resp.status_code}): {error_msg}")
        except Exception as e:
            print(f"OpenAI Chat Exception: {e}")
            all_errors.append(f"OpenAI: {str(e)}")

    if result_content:
        return result_content
    
    error_detail = " | ".join(all_errors) if all_errors else "Niciun API Key valid."
    return f"Eroare: Nu am putut obține un răspuns. Detalii: {error_detail}"

