with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
    backend = f.read()

import re

# 1. Bump timeout to 9.5s
backend = backend.replace('timeout=8', 'timeout=9.5')

# 2. Prioritize gemini-1.5-flash for speed
old_list = 'models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]'
new_list = 'models_to_try = ["gemini-1.5-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]'
backend = backend.replace(old_list, new_list)

# 3. Handle timeout exceptions silently and move to the next model!
old_logic = """    except Exception as e:
        return {"error": str(e)}"""

new_logic = """    except requests.exceptions.ReadTimeout as e:
        # If all models timed out, return the timeout error
        return {"error": f"Toate modelele au depasit timpul limita (timeout). Te rugam sa incerci din nou. Ultimul model: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}"""

# We need to catch timeout *inside* the loop so it falls back!
# Wait, let's just do a string replace of the entire block to be precise.

old_try_block = """        models_to_try = ["gemini-1.5-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
        for idx, model in enumerate(models_to_try):
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}",
                json=payload, timeout=9.5
            )
            data = resp.json()
            
            # If there's an error (e.g. 429 Quota, 503 Unavailable), try the next model
            if "error" in data:
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

new_try_block = """        models_to_try = ["gemini-1.5-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
        last_error = ""
        for idx, model in enumerate(models_to_try):
            try:
                resp = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}",
                    json=payload, timeout=8.5  # Adjusted back to 8.5 to allow loop to try multiple within 10s if one fails fast
                )
                data = resp.json()
                
                # If there's an error (e.g. 429 Quota, 503 Unavailable), try the next model
                if "error" in data:
                    last_error = f"API Error: {data}"
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
            except requests.exceptions.ReadTimeout as e:
                last_error = f"Timeout ({model})"
                if idx < len(models_to_try) - 1:
                    continue
            except Exception as e:
                last_error = f"Exception ({model}): {str(e)}"
                if idx < len(models_to_try) - 1:
                    continue
                    
        return {"error": f"Toate modelele au eșuat. Ultimul motiv: {last_error}"}
    except Exception as e:
        return {"error": str(e)}"""

backend = backend.replace(old_try_block, new_try_block)

with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
    f.write(backend)

print("Patch applied")
