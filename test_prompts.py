import requests, os, json
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('GEMINI_API_KEY') or os.getenv('gemini')
if not api_key:
    print('No API Key')
    exit()

title = 'What I Saw at the Lincoln Memorial Reflecting Pool Monday Afternoon - WSJ'
url = 'https://www.wsj.com/articles/what-i-saw-at-the-lincoln-memorial-reflecting-pool-monday-afternoon-8e9a2b1c'

for prompt in [
    f"I need to extract the full text of the following news article. Title: '{title}'. URL: {url}. Please search the web for this article title or content, and provide the FULL TEXT of the article. Do not include introductory text, just return the article content formatted with paragraphs.",
    f"Search the web for the exact article titled '{title}'. Provide a highly detailed, comprehensive summary of the article, covering all key facts, paragraphs, quotes, and figures mentioned. Format it beautifully with HTML <p> tags."
]:
    payload = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'tools': [{'google_search': {}}]}
    resp = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}', json=payload)
    data = resp.json()
    if 'candidates' in data:
        print('SUCCESS:', len(data['candidates'][0]['content']['parts'][0]['text']))
    else:
        print('FAILED:', data)
