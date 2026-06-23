import re

with open('api/kpi_audit.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the overly rigid llm_research_prompt and search_engine_query
old_prompt = """    # The query for the raw search engines (Tavily, Brave, DDG) - needs to be concise!
    search_engine_query = f"{ticker} stock {message}"

    # The prompt for the LLM researcher (Gemini) - needs instructions!
    llm_research_prompt = f"Search the web deeply for this query: '{message}' for the company {ticker}. If the user asks about earnings estimates, specifically search Nasdaq for multi-year EPS estimates. If they ask about SEC filings, 10-K, 10-Q, presentations, or earnings transcripts, extract exact numbers and management quotes.\""""

new_prompt = """    # The query for the raw search engines (Tavily, Brave, DDG) - needs to be concise!
    # Strip common conversational fluff that confuses search engines
    clean_message = message.lower().replace('ce', '').replace('estimari', 'estimates').replace('avem', '').replace('pentru', '').replace('perioada', '').replace('in eps', 'eps').replace('?', '').strip()
    search_engine_query = f"{ticker} stock {clean_message}"

    # The prompt for the LLM researcher (Gemini) - needs instructions!
    llm_research_prompt = f"Perform a comprehensive web search to answer the following query: '{message}' for the company {ticker}. If the user asks about earnings/EPS/Revenue estimates for specific years (e.g. 2026-2029), DO NOT restrict your search to Nasdaq. Search across all major financial aggregators (SeekingAlpha, WallStreetZen, MarketBeat, Yahoo Finance, etc.) to find the consensus estimates for EACH year requested. Return the exact numerical estimates found. Do not invent numbers. If they ask about SEC filings, extract exact quotes and numbers.\""""

content = content.replace(old_prompt, new_prompt)

with open('api/kpi_audit.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Search logic patched")
