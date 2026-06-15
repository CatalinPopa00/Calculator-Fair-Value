import os
import requests
import json
from dotenv import load_dotenv

load_dotenv('.env.local')
gemini_key = os.environ.get('GEMINI_API_KEY')

gemini_payload = {
    "contents": [{"role": "user", "parts": [{"text": "Search the web for recent data regarding UBER estimates."}]}],
    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600},
    "tools": [{"googleSearch": {}}]
}

resp = requests.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
    headers={"Content-Type": "application/json"},
    json=gemini_payload,
    timeout=15
)
print(resp.status_code)
print(resp.text)
