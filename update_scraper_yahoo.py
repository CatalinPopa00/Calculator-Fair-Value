with open('scraper/yahoo.py', 'r') as f:
    content = f.read()

target = """        data = {
            "ticker": ticker_symbol.upper(),
            "name": name,
            "currency": info.get("currency", "USD"),"""

replacement = """        data = {
            "ticker": ticker_symbol.upper(),
            "name": name,
            "open": info.get("regularMarketOpen") or info.get("open") or info.get("previousClose") or prev_close,
            "currency": info.get("currency", "USD"),"""

content = content.replace(target, replacement)

with open('scraper/yahoo.py', 'w') as f:
    f.write(content)
