import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)
tavily_key = os.environ.get("TAVILY_API_KEY")

research_query = "Search the web deeply for this query: 'Ce eps estimates ne da nasdaq pentru perioada 2026-2028?' for the company MSFT. If the user asks about earnings estimates, specifically search Nasdaq for multi-year EPS estimates."

resp = requests.post(
    "https://api.tavily.com/search",
    headers={"Content-Type": "application/json"},
    json={
        "api_key": tavily_key,
        "query": research_query,
        "search_depth": "advanced",
        "include_answer": True,
        "max_results": 5
    },
    timeout=15
)
data = resp.json()
print("ANSWER:", data.get("answer"))
print("\nRESULTS:")
for r in data.get("results", []):
    print(f"- {r.get('url')}: {r.get('content')[:200]}...")
