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
                    if valid_end and valid_end[0].start() - idx < 60000:
                        report_text = text[idx:valid_end[0].start()]
                    else:
                        report_text = text[idx:idx+60000]
                        
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
                    if valid_end and valid_end[0].start() - idx < 40000:
                        report_text = text[idx:valid_end[0].start()]
                    else:
                        report_text = text[idx:idx+40000]
                        
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


def get_fmp_transcripts(ticker: str) -> str:
    """Încearcă extragerea transcrierilor oficiale dacă există API Key FMP, altfel Fallback pe Yahoo News."""
    fmp_key = os.getenv("FMP_API_KEY")
    if not fmp_key:
        print("FMP_API_KEY missing, falling back to SEC 10-K Reports.")
        sec_text = _get_sec_10k_text(ticker)
        yahoo_text = _get_yahoo_earnings_news(ticker)
        return sec_text + "\n\n" + yahoo_text
        
    try:
        # Obține lista de transcrieri disponibile
        url = f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{ticker}?apikey={fmp_key}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        if not data or not isinstance(data, list):
            print("No FMP transcripts found, falling back to SEC.")
            sec_text = _get_sec_10k_text(ticker)
            yahoo_text = _get_yahoo_earnings_news(ticker)
            return sec_text + "\n\n" + yahoo_text
            
        # Păstrăm cele mai recente 20 trimestre (aprox. 5 ani istoric)
        recent_calls = data[:20]
        combined_transcripts = ""
        
        for call in recent_calls:
            q = call.get('quarter')
            y = call.get('year')
            content = call.get('content', '')
            # Scurtăm conținutul pentru a evita token limits (primele 15.000 caractere)
            combined_transcripts += f"\n\n--- Earnings Call Q{q} {y} ---\n{content[:15000]}"
            
        if not combined_transcripts.strip():
            sec_text = _get_sec_10k_text(ticker)
            yahoo_text = _get_yahoo_earnings_news(ticker)
            return sec_text + "\n\n" + yahoo_text
            
        return combined_transcripts
        
    except Exception as e:
        print(f"Error fetching FMP transcripts for {ticker}: {e}")
        sec_text = _get_sec_10k_text(ticker)
        yahoo_text = _get_yahoo_earnings_news(ticker)
        return sec_text + "\n\n" + yahoo_text

def run_ai_kpi_audit(ticker: str) -> Dict[str, Any]:
    ticker = ticker.upper()
    if ticker in audit_cache:
        return audit_cache[ticker]

    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except:
        pass

    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("gemini")
    groq_key = os.getenv("GROQ_API_KEY")

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
    
    if not raw_text or len(raw_text) < 500:
        return {
            "error": True,
            "detail": f"Could not find enough recent financial reports or press releases for {ticker}."
        }

    system_prompt = '''
You are a top-tier Wall Street Financial Analyst & Data Extraction AI. 
You will receive a set of texts extracted from the most recent Earnings Calls or SEC reports for a specific company.
These texts cover up to 5 years of financial history.

YOUR MISSION:
Identify up to 8 of the MOST CRITICAL, COMPANY-SPECIFIC, OPERATIONAL Key Performance Indicators (KPIs).

CRITICAL KPI SELECTION RULES (STRICTLY ENFORCED):
1. ONLY extract OPERATIONAL and BUSINESS-SPECIFIC qualitative metrics. Think like a hedge fund analyst.
2. EXAMPLES OF GOOD KPIs: ARR (Annual Recurring Revenue), AI Monetization Revenue, Cloud Segments, Subscriber counts, DAU/MAU, Room Nights, Gross Bookings, Segment Revenue splits, Engagement metrics, Same-Store Sales.
3. ABSOLUTELY DO NOT extract generic accounting or balance sheet items! BANNED METRICS: Deferred Revenue, Common Stock, Operating Expenses, Cash Flow, Goodwill, Debt, Amortization, Total Assets, Revenue, Net Income, EPS, Profit, Gross Margin, R&D Expenses. (The user already has these in their financial statements tab!).
4. Focus entirely on what drives the business conceptually and structurally.

VALUE EXTRACTION (5-YEAR HISTORY + RECENT QUARTERS):
For each identified KPI, track their evolution over the last 5 full fiscal years (e.g., FY 2021, FY 2022, FY 2023, FY 2024, FY 2025).
ADDITIONALLY, for the CURRENT unfinished fiscal year, extract the available individual quarterly data (e.g., FY 2026 Q1, FY 2026 Q2).
Format the keys EXACTLY as "FY [Year]" or "FY [Year] Q[X]". Ensure exact numbers are extracted if explicitly stated. Format numbers cleanly (e.g. "1.2 Billion", "34.5%", "450 Million"). 

CRITICAL EXTRACTION RULE: You MUST extract the value for EVERY single year provided in the text. You are dealing with a massive text. Do NOT be lazy. Scan every single [Year ...] section carefully.
CRITICAL FALLBACK FOR MISSING DATA: The provided text is heavily truncated and might miss historical or recent data. If a value for a specific period is absent from the provided text, YOU MUST ACTIVELY USE YOUR OWN INTERNAL KNOWLEDGE BASE to fill in the real numerical data for that KPI! Do NOT be lazy and do NOT use "N/A" or empty values unless you genuinely cannot find the data in your vast internal memory! You are a powerful AI with deep financial knowledge, act like one and fill in ALL missing historical and recent blanks to create a perfectly complete trend without any empty gaps!

UNITY AND CONSISTENCY RULE (CRITICAL):
To ensure the frontend table aligns perfectly, EVERY SINGLE KPI MUST HAVE THE EXACT SAME SET OF PERIOD KEYS in the 'values' object.
1. Determine the global master set of periods available across all data (e.g. "FY 2022", "FY 2023", "FY 2024", "FY 2025", "FY 2026 Q1", "FY 2026 Q2").
2. Use this EXACT same set of keys for EVERY KPI.
3. If a specific KPI is missing data for a period, you MUST still include the key and set its value to "N/A" or "-" (e.g. "FY 2026 Q2": "N/A"). Do NOT omit keys for any KPI. The number of keys and the names of the keys must be 100% identical across all KPIs.

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
        result_content = None
        all_errors = []

        # Try Gemini First
        if gemini_key:
            models_to_try = [
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-1.5-pro"
            ]
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [{"text": f"{system_prompt}\n\nAici sunt textele pentru {ticker}:\n\n{raw_text}"}]
                }],
                "generationConfig": {"temperature": 0.2}
            }
            for idx, model in enumerate(models_to_try):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=90)
                    if resp.status_code == 200:
                        data = resp.json()
                        try:
                            if "candidates" in data and data["candidates"]:
                                result_content = data["candidates"][0]["content"]["parts"][0]["text"]
                                break
                        except (KeyError, IndexError):
                            all_errors.append(f"Gemini {model} blocked or missing text parts")
                    elif resp.status_code == 429:
                        print(f"Gemini Fallback Rate Limit (429) hit for {model}. Retrying next model...")
                        all_errors.append(f"Gemini {model}: 429 Rate Limit")
                        if idx < len(models_to_try) - 1:
                            import time
                            time.sleep(2)
                    else:
                        error_msg = resp.text
                        try:
                            err_data = resp.json()
                            if "error" in err_data and "message" in err_data["error"]:
                                error_msg = err_data["error"]["message"]
                        except:
                            pass
                        all_errors.append(f"Gemini {model}: {error_msg}")
                except Exception as e:
                    all_errors.append(f"Gemini {model} Timeout/Error: {str(e)}")

        # Try Groq as fallback
        if not result_content and groq_key:
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
            try:
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=55)
                if resp.status_code == 200:
                    data = resp.json()
                    result_content = data["choices"][0]["message"]["content"]
                else:
                    error_msg = resp.text
                    try:
                        error_msg = resp.json().get("error", {}).get("message", resp.text)
                    except:
                        pass
                    all_errors.append(f"Groq Error: {error_msg}")
            except Exception as e:
                all_errors.append(f"Groq Timeout/Error: {str(e)}")

        # Try OpenAI as final fallback
        if not result_content and openai_key:
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
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=55)
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

    # Build base system prompt (without live research yet)
    base_system_prompt = f"""
You are "Babi AI", an elite, highly critical Wall Street Financial Analyst integrated into the 'Babi Calculator-inatorul' dashboard.
The user is currently analyzing the ticker: {ticker}.
Here is the real-time context of the company you MUST use to answer their questions:
- Current Price: {context.get('price')}
- Estimated Fair Value: {context.get('fairValue')}
- Margin of Safety: {context.get('marginOfSafety')}
- Recent News Headlines: {context.get('news', 'N/A')}
- AI KPI Audit Summary: {context.get('kpiSummary', 'N/A')}
- Risk Red Flags: {context.get('redFlags', 'N/A')}
- Business Summary: {context.get('businessSummary', 'N/A')}
- Analyst Estimates & Targets: {context.get('estimates', 'N/A')}
"""

    instructions = """
Instructions:
1. **Conversational Continuity & Deep Competence:** Actively track the flow of the conversation. Fully understand the user's task and provide a highly competent, comprehensive, and convincing response. Do not be dry ("sec") or superficial. Elaborate on your reasoning, connect the dots, and write extensively like a top-tier analyst.
2. **Proactive Document Research:** You must know how to proactively search for and reference data from Yearly/Quarterly reports (10-K, 10-Q), investor presentations, and earnings call transcripts.
3. **Quote Formatting Rule:** When you provide a direct quote, DO NOT use quotation marks ("" or '') and DO NOT use italics. Instead, put a colon (:) at the end of your introductory sentence, write the quote on a completely new line, and leave a blank empty line before and after the quote to separate it from the rest of the text.
Example:
Managementul a subliniat recent o schimbare majoră de strategie:

Observăm o cerere fără precedent pentru noile noastre modele de AI, ceea ce ne-a determinat să accelerăm investițiile în infrastructură.

Această afirmație confirmă teza conform căreia...
4. **Nasdaq Earnings Estimates & CAGR:** If the user asks about earnings estimates on multiple years, you must read the earnings estimates (from Nasdaq or other sources) for those specific years, list the EPS estimates explicitly, and ALWAYS automatically calculate the Compound Annual Growth Rate (CAGR) between those years to show the growth trajectory.
5. **Live Research Integration:** If LIVE RESEARCH DATA is provided above, use it extensively to answer the user's question with facts from TODAY.
6. **KNOWLEDGE CUTOFF OVERRIDE:** You MUST IGNORE your internal 'Cutting Knowledge Date'. You DO have access to real-time data through the LIVE RESEARCH DATA block. NEVER say your knowledge is limited to a past date.
7. **INTERNET SEARCH DIAGNOSTIC:** If the user explicitly asks you to search the internet, and the LIVE RESEARCH DATA block is completely empty or missing, you MUST reply EXACTLY with this: "Eroare de sistem: Cheia GEMINI_API_KEY lipsește sau este invalidă în Vercel, astfel că modulul meu de căutare web a eșuat în fundal. Te rog să o verifici."
8. **Tone & Language:** Speak natively and naturally in Romanian. Be highly confident, professional, engaging, and deeply analytical.
"""

    live_research_data = ""
    result_content = None
    all_errors = []

    # MULTI-MODEL PIPELINE: Phase 1 (Gemini Researcher)
    if gemini_key and groq_key:
        try:
            research_query = f"Search the web deeply for this query: '{message}' for the company {ticker}. If the user asks about earnings estimates, specifically search Nasdaq for multi-year EPS estimates. If they ask about SEC filings, 10-K, 10-Q, presentations, or earnings transcripts, extract exact numbers and management quotes. Return detailed bullet points with raw data, financial figures, and exact quotes."
            gemini_payload = {
                "contents": [{"role": "user", "parts": [{"text": research_query}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
                "tools": [{"googleSearch": {}}]
            }
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                headers={"Content-Type": "application/json"},
                json=gemini_payload,
                timeout=15
            )
            if resp.status_code == 200:
                live_research_data = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                print(f"Gemini Research Error (status {resp.status_code}): {resp.text[:200]}")
        except Exception as e:
            print(f"Gemini Research Exception: {e}")

    # Build Final System Prompt
    system_prompt = base_system_prompt
    if live_research_data:
        system_prompt += f"- LIVE RESEARCH DATA (from your AI Assistant): {live_research_data}\n"
    system_prompt += instructions

    # Prepare message history
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        api_role = "assistant" if msg["role"] == "ai" else "user"
        messages.append({"role": api_role, "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    # MULTI-MODEL PIPELINE: Phase 2 (Groq Analyst)
    if groq_key:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"},
                json={"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.5},
                timeout=30
            )
            if resp.status_code == 200:
                result_content = resp.json()["choices"][0]["message"]["content"]
            else:
                error_msg = resp.text[:200]
                print(f"Groq Chat Error (status {resp.status_code}): {error_msg}")
                all_errors.append(f"Groq({resp.status_code}): {error_msg}")
        except Exception as e:
            print(f"Groq Chat Exception: {e}")
            all_errors.append(f"Groq: {str(e)}")

    # Fallback: If pipeline failed (or Groq is missing), just use Gemini as a standard chat model
    if not result_content and gemini_key:
        try:
            gemini_messages = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in messages if m["role"] != "system"]
            gemini_payload = {
                "contents": gemini_messages,
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "generationConfig": {"temperature": 0.5, "maxOutputTokens": 1024},
                "tools": [{"googleSearch": {}}]
            }
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                headers={"Content-Type": "application/json"},
                json=gemini_payload,
                timeout=30
            )
            if resp.status_code == 200:
                result_content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                error_msg = resp.text[:200]
                print(f"Gemini Chat Error (status {resp.status_code}): {error_msg}")
                all_errors.append(f"Gemini({resp.status_code}): {error_msg}")
        except Exception as e:
            print(f"Gemini Chat Exception: {e}")
            all_errors.append(f"Gemini: {str(e)}")

    # Fallback: OpenAI
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

