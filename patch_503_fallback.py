with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
    backend = f.read()

old_fallback = """            # If rate limited (429) or quota exceeded, try the next model
            if "error" in data and data["error"].get("code") == 429:
                if idx < len(models_to_try) - 1:
                    continue"""

new_fallback = """            # If there's an error (e.g. 429 Quota, 503 Unavailable), try the next model
            if "error" in data:
                if idx < len(models_to_try) - 1:
                    continue"""

backend = backend.replace(old_fallback, new_fallback)

# To be absolutely sure, let's also add 503 to the check if replace didn't work exactly
import re
backend = re.sub(
    r'if "error" in data and data\["error"\].get\("code"\) == 429:',
    r'if "error" in data:',
    backend
)

with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
    f.write(backend)

print("Fallback updated for 503 errors")
