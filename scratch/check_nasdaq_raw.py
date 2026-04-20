
import urllib.request
import json

ticker = "HIMS"
url = f"https://api.nasdaq.com/api/analyst/{ticker}/earnings-forecast"
headers = {
    'User-Agent': "Mozilla/5.0",
    'Accept': 'application/json'
}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())
    print(json.dumps(data, indent=2))
