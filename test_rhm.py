import os
import sys
import json
import requests
sys.path.append(os.path.abspath('.'))

from api.kpi_audit import _get_yahoo_earnings_news
yahoo_text = _get_yahoo_earnings_news('RHM.DE')

system_prompt = '''You are a top-tier Wall Street Financial Analyst & Data Extraction AI. 
...
CRITICAL: If a value for a specific period is completely absent from the text (which often happens for European companies without SEC filings), YOU MUST USE YOUR OWN INTERNAL KNOWLEDGE BASE to fill in the real historical numerical data (FY 2020 - FY 2025) for that KPI! Do NOT use "N/A" unless you genuinely cannot find the data in your vast internal memory! You are a powerful AI, act like one and fill in the missing blanks.
...'''

# Wait I will use my key instead to avoid rate limit!
gemini_key = os.getenv('GEMINI_API_KEY')
if not gemini_key:
    from dotenv import load_dotenv
    load_dotenv('.env')
    gemini_key = os.getenv('GEMINI_API_KEY') or os.getenv('gemini')

url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}'
headers = {'Content-Type': 'application/json'}
payload = {
    'contents': [{'parts': [{'text': f'{system_prompt}\n\nAici sunt textele pentru RHM.DE:\n\n{yahoo_text}'}]}],
    'generationConfig': {'temperature': 0.2, 'responseMimeType': 'application/json'}
}
resp = requests.post(url, headers=headers, json=payload)
print(resp.text)
