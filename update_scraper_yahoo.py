with open('scraper/yahoo.py', 'r') as f:
    content = f.read()

target = """        return {
            "name": name,
            "sector": sector,
            "industry": industry,"""

replacement = """        return {
            "name": name,
            "sector": sector,
            "industry": industry,
            "open": info.get("regularMarketOpen") or info.get("open") or info.get("previousClose") or prev_close,"""

content = content.replace(target, replacement)

with open('scraper/yahoo.py', 'w') as f:
    f.write(content)
