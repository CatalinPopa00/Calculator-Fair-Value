with open('api/index.py', 'r') as f:
    content = f.read()

target = """            "company_profile": {
                "industry": data.get("industry") or "N/A",
                "sector": data.get("sector") or "N/A","""

replacement = """            "company_profile": {
                "industry": data.get("industry") or "N/A",
                "sector": data.get("sector") or "N/A",
                "open_price": sanitize(data.get("open") or data.get("regularMarketOpen") or data.get("previousClose") or current_price),"""

content = content.replace(target, replacement)

with open('api/index.py', 'w') as f:
    f.write(content)
