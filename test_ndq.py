import sys, json, urllib.request
sys.path.insert(0, 'backend')

# Fetch Nasdaq PLTR
url = "https://api.nasdaq.com/api/analyst/PLTR/earnings-forecast"
headers = {'User-Agent': 'Mozilla/5.0'}
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        print("REV ROWS:", json.dumps(data.get('data', {}).get('revenueForecast', {}).get('rows', []), indent=2))
        print("EPS ROWS:", json.dumps(data.get('data', {}).get('quarterlyForecast', {}).get('rows', []), indent=2))
except Exception as e:
    print(e)
