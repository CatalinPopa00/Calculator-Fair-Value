import urllib.request
import json

ticker = "HIMS"
url = f'https://api.nasdaq.com/api/analyst/{ticker}/earnings-forecast'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=5) as response:
    data = json.loads(response.read())
    print(json.dumps(data, indent=2))
