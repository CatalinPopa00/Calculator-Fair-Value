with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
    backend = f.read()

old_payload = """    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}]
    }"""

new_payload = """    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }"""

backend = backend.replace(old_payload, new_payload)

# Let's also make sure that if candidates is still empty, we return the EXACT raw response from Gemini
old_else = """        else:
            return {"error": "Could not extract article content. The paywall might be blocking the AI or the article was not found in public search."}"""
new_else = """        else:
            return {"error": f"AI Blocked. Raw response: {data}"}"""

backend = backend.replace(old_else, new_else)

with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
    f.write(backend)

print("Payload updated")
