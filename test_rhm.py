import os
import sys
import json
from dotenv import load_dotenv
import requests

sys.path.append(os.path.abspath('.'))
load_dotenv('.env.local')

from api.kpi_audit import _get_yahoo_earnings_news

yahoo_text = _get_yahoo_earnings_news('RNMBY')

system_prompt = '''You are a top-tier Wall Street Financial Analyst & Data Extraction AI. 
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
For each identified KPI, search deeply and track their evolution over time over the last 5 full fiscal years (e.g., FY 2021, FY 2022, FY 2023, FY 2024, FY 2025).
ADDITIONALLY, for the CURRENT unfinished fiscal year, extract the available individual quarterly data (e.g., FY 2026 Q1, FY 2026 Q2). Do NOT use estimates.
Format the keys EXACTLY as "FY [Year]" or "FY [Year] Q[X]". Ensure exact numbers are extracted if explicitly stated. Format numbers cleanly (e.g. "1.2 Billion", "34.5%", "450 Million"). If a value for a specific period is completely absent from the text, use "N/A", but TRY YOUR BEST to infer the values from textual descriptions if tables are omitted.

Return ONLY a valid JSON object, strictly following this EXACT structure:
{
  "company": "Ticker",
  "audit_summary": "A short paragraph summarizing the quality of the business deduced from these indicators.",
  "kpis": [
    {
      "name": "KPI Name",
      "description": "What it represents and why it is important for this company.",
      "values": {
        "FY 2020": "1.5M",
        "FY 2021": "1.8M",
        "FY 2022": "2.2M",
        "FY 2023": "2.8M",
        "FY 2024": "3.1M"
      }
    }
  ]
}'''

gemini_key = os.getenv('GEMINI_API_KEY')
if not gemini_key:
    print('No key')
else:
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}'
    headers = {'Content-Type': 'application/json'}
    payload = {
        'contents': [{'parts': [{'text': f'{system_prompt}\n\nAici sunt textele pentru RNMBY:\n\n{yahoo_text}'}]}],
        'generationConfig': {'temperature': 0.2, 'responseMimeType': 'application/json'}
    }
    resp = requests.post(url, headers=headers, json=payload)
    print(resp.json()['candidates'][0]['content']['parts'][0]['text'])
