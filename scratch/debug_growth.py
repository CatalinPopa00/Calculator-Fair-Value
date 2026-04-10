
import json
import urllib.request
import random
import datetime

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def get_random_agent():
    return random.choice(USER_AGENTS)

def safe_nasdaq_float(val):
    if val is None or str(val).strip() == "" or str(val).upper() == "N/A": 
        return None
    if isinstance(val, (int, float)): return float(val)
    try:
        clean_val = str(val).replace('$', '').replace(',', '').strip()
        if not clean_val: return None
        return float(clean_val)
    except: return None

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
        except Exception as e: return None
    eps_data = fetch_url("eps", ticker)
    if eps_data:
        results["yearly_eps"] = eps_data.get('data', {}).get('yearlyForecast', {}).get('rows', [])
    return results

def get_nasdaq_actual_eps(ticker: str) -> float:
    try:
        url = f'https://api.nasdaq.com/api/company/{ticker.upper()}/earnings-surprise'
        headers = {'User-Agent': get_random_agent()}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read())
        rows = data.get('data', {}).get('earningsSurpriseTable', {}).get('rows', [])
        if rows:
            total_eps = 0.0
            count = 0
            for row in rows[:4]:
                val_str = row.get('eps') or row.get('actualEPS')
                if val_str:
                    try:
                        total_eps += float(val_str)
                        count += 1
                    except ValueError: continue
            if count >= 3:
                return (total_eps / count) * 4.0
    except Exception as e:
        print(f"Error fetching actual: {e}")
    return None

def get_nasdaq_earnings_growth_debug(ticker: str, trailing_eps: float) -> float:
    if not trailing_eps or trailing_eps <= 0:
        return None
    try:
        nq_data = get_nasdaq_comprehensive_estimates(ticker)
        rows = nq_data.get("yearly_eps", [])
        if not rows: 
            print("No yearly_eps rows found")
            return None
        
        actual_eps_base = get_nasdaq_actual_eps(ticker)
        print(f"Actual EPS base (Nasdaq): {actual_eps_base}")
            
        base_eps = actual_eps_base if actual_eps_base and actual_eps_base > 0 else trailing_eps
        print(f"Using base EPS: {base_eps}")
        
        eps_values = [base_eps]
        for row in rows[:3]:
            val = safe_nasdaq_float(row.get('consensusEPSForecast'))
            print(f"Forecast row {row.get('fiscalEnd')}: {val}")
            if val is not None and val > 0:
                eps_values.append(val)
        
        print(f"EPS values for growth calculation: {eps_values}")
        
        if len(eps_values) < 2: 
            print("Not enough EPS values for growth calculation")
            return None
        
        growths = []
        for i in range(1, len(eps_values)):
            prev = eps_values[i-1]
            curr = eps_values[i]
            if prev > 0:
                growth = (curr - prev) / prev
                print(f"Growth step {i}: {growth}")
                clamped_growth = min(max(growth, -0.5), 1.5)
                growths.append(clamped_growth)
        
        if not growths: return None
        
        avg_growth = sum(growths) / len(growths)
        print(f"Average Growth: {avg_growth}")
        return avg_growth

    except Exception as e:
        print(f"Error: {e}")
    return None

if __name__ == "__main__":
    get_nasdaq_earnings_growth_debug("ADBE", 16.0)
