import requests
import json

def get_nasdaq_actual_eps(ticker):
    try:
        url = f'https://api.nasdaq.com/api/company/{ticker.upper()}/earnings-surprise'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            rows = data.get('data', {}).get('earningsSurpriseTable', {}).get('rows', [])
            if rows:
                total_eps = 0.0
                count = 0
                print(f"--- Nasdaq Earnings Surprise for {ticker} ---")
                for row in rows[:4]:
                    val = row.get('eps') or row.get('actualEPS')
                    print(f"Date: {row.get('dateReported')}, EPS: {val}")
                    if val:
                        total_eps += float(val)
                        count += 1
                if count > 0:
                    return (total_eps / count) * 4.0
    except Exception as e:
        print(f"Error: {e}")
    return None

if __name__ == "__main__":
    eps = get_nasdaq_actual_eps("META")
    print(f"\nNasdaq Sum (last 4 Qs scaled to 4): {eps}")
