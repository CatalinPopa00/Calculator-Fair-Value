
import urllib.request
import json
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def get_nasdaq_chart(ticker):
    url = f'https://api.nasdaq.com/api/company/{ticker}/earnings-surprise'
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=7) as response:
        data = json.loads(response.read())
        chart = data.get('data', {}).get('chart', [])
        print(f"Ticker: {ticker}")
        print(f"Total points in chart: {len(chart)}")
        if chart:
            import datetime
            for item in chart[-8:]:
                dt = datetime.datetime.fromtimestamp(int(item['x']), tz=datetime.timezone.utc)
                print(f"Date: {dt}, EPS: {item['y']}")

if __name__ == "__main__":
    get_nasdaq_chart("ADBE")
    get_nasdaq_chart("META")
