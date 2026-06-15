import io
import re

with io.open('api/index.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add synthesis_cache
target_cache = "valuation_cache = TTLCache(maxsize=1000, ttl=60 * 60)"
replace_cache = "valuation_cache = TTLCache(maxsize=1000, ttl=60 * 60)\nsynthesis_cache = TTLCache(maxsize=500, ttl=86400 * 7)"

if 'synthesis_cache = TTLCache' not in text:
    text = text.replace(target_cache, replace_cache)

# Update get_synthesis route
target_route_start = """def get_synthesis(ticker: str, response: Response):
    # Set Vercel Edge Cache headers for synthesis (Cache 1hr, stale up to 24hr)
    response.headers["Cache-Control"] = "public, s-maxage=3600, stale-while-revalidate=86400"

    ticker_upper = ticker.upper()
    try:"""

replace_route_start = """def get_synthesis(ticker: str, response: Response):
    # Set Vercel Edge Cache headers for synthesis (Cache 1hr, stale up to 24hr)
    response.headers["Cache-Control"] = "public, s-maxage=3600, stale-while-revalidate=86400"

    ticker_upper = ticker.upper()
    
    # Check memory cache first to avoid re-running Gemini on large transcripts
    if ticker_upper in synthesis_cache:
        return {"ticker": ticker_upper, "company_overview_synthesis": synthesis_cache[ticker_upper]}

    try:"""

if 'if ticker_upper in synthesis_cache:' not in text:
    text = text.replace(target_route_start, replace_route_start)

# Update the return to set cache
target_route_return = """        # 3. Call get_company_synthesis with run_ai=True to invoke Gemini API
        synthesis = get_company_synthesis(ticker_upper, info, run_ai=True)
        return {"ticker": ticker_upper, "company_overview_synthesis": synthesis}"""

replace_route_return = """        # 3. Call get_company_synthesis with run_ai=True to invoke Gemini API
        synthesis = get_company_synthesis(ticker_upper, info, run_ai=True)
        synthesis_cache[ticker_upper] = synthesis
        return {"ticker": ticker_upper, "company_overview_synthesis": synthesis}"""

if 'synthesis_cache[ticker_upper] = synthesis' not in text:
    text = text.replace(target_route_return, replace_route_return)

with io.open('api/index.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated api/index.py")
