
import json
import urllib.request
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def get_random_agent():
    return random.choice(USER_AGENTS)

def get_nasdaq_comprehensive_estimates(ticker: str) -> dict:
    ticker = ticker.upper()
    results = {"yearly_eps": [], "quarterly_eps": [], "yearly_rev": [], "quarterly_rev": []}
    
    def fetch_url(url_type, t_sym):
        endpoint = "earnings-forecast" if url_type == "eps" else "revenue-forecast"
        try:
            url = f'https://api.nasdaq.com/api/analyst/{t_sym}/{endpoint}'
            headers = {'User-Agent': get_random_agent()}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=7) as response:
                return json.loads(response.read())
        except Exception as e: 
            print(f"Error fetching {url_type}: {e}")
            return None

    eps_data = fetch_url("eps", ticker)
    if eps_data:
        results["yearly_eps"] = eps_data.get('data', {}).get('yearlyForecast', {}).get('rows', [])
    
    return results

if __name__ == "__main__":
    data = get_nasdaq_comprehensive_estimates("ADBE")
    print(json.dumps(data, indent=2))
