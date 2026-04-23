
import urllib.request
import json
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def get_yahoo_eps_trend(ticker_symbol: str) -> dict:
    try:
        url = (
            f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker_symbol.upper()}"
            f"?modules=earningsTrend"
        )
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            trends = data['quoteSummary']['result'][0]['earningsTrend']['trend']
            result = {}
            for t in trends:
                p = t.get('period')
                if p in ['0y', '+1y', '0q', '+1q']:
                    result[p] = {
                        "yearAgoEps": t.get('growth', {}).get('yearAgoEps', {}).get('raw'),
                        "currentEstimate": t.get('estimate', {}).get('raw')
                    }
            return result
    except Exception as e:
        print(f"Yahoo Trend check failed: {e}")
        return {}

ticker = "UBER"
res = get_yahoo_eps_trend(ticker)
print(f"\n--- Yahoo Earnings Trend for {ticker} ---")
print(json.dumps(res, indent=2))
