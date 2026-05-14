import urllib.request, json, time
url = 'https://babi-calculator-inatorul.vercel.app/api/valuation/ADBE?bust=' + str(time.time())
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    data = json.loads(urllib.request.urlopen(req).read())
    peers = data.get('company_profile', {}).get('competitor_metrics', [])
    print("LIVE VERCEL PEERS:", [(c.get('ticker'), c.get('peg_ratio')) for c in peers])
except Exception as e:
    print("Error:", e)
