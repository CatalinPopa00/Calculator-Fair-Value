with open('api/macro_routes.py', 'a', encoding='utf-8') as f:
    f.write('''

@router.get("/api/read-article")
def read_article(url: str, title: str = ""):
    import os, requests
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("gemini")
    if not gemini_key:
        return {"error": "No Gemini API Key available to read article"}
        
    prompt = f"I need to extract the full text of the following news article. Title: '{title}'. URL: {url}. Please search the web for this article title or content, and provide the FULL TEXT of the article. Do not include introductory text, just return the article content formatted with paragraphs."
    
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}]
    }
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
            json=payload, timeout=15
        )
        data = resp.json()
        if "candidates" in data and len(data["candidates"]) > 0:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            # Clean up the output if Gemini wraps it in markdown blockquotes or introduces it
            return {"text": content}
        else:
            return {"error": "Could not extract article content. The paywall might be blocking the AI or the article was not found in public search."}
    except Exception as e:
        return {"error": str(e)}
''')
print("Endpoint appended")
