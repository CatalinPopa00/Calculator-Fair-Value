with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
    backend = f.read()

old_logic = """    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
            json=payload, timeout=8
        )
        data = resp.json()
        if "candidates" in data and len(data["candidates"]) > 0:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            
            if content.startswith('```html'): content = content[7:]
            if content.startswith('```'): content = content[3:]
            if content.endswith('```'): content = content[:-3]
            content = content.strip()

            return {"text": content}
        else:
            return {"error": f"AI Blocked. Raw response: {data}"}
    except Exception as e:
        return {"error": str(e)}"""

new_logic = """    try:
        models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
        for idx, model in enumerate(models_to_try):
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}",
                json=payload, timeout=8
            )
            data = resp.json()
            
            # If rate limited (429) or quota exceeded, try the next model
            if "error" in data and data["error"].get("code") == 429:
                if idx < len(models_to_try) - 1:
                    continue
            
            # If successful
            if "candidates" in data and len(data["candidates"]) > 0:
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                
                if content.startswith('```html'): content = content[7:]
                if content.startswith('```'): content = content[3:]
                if content.endswith('```'): content = content[:-3]
                content = content.strip()

                return {"text": content}
            
            # If blocked for safety but not rate limited, just return the error immediately
            return {"error": f"AI Blocked ({model}). Raw response: {data}"}
            
    except Exception as e:
        return {"error": str(e)}"""

backend = backend.replace(old_logic, new_logic)

with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
    f.write(backend)

print("Fallback logic injected")
