import requests
url = "https://finance.yahoo.com/quote/ADBE/analysis"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers)
with open("adbe_analysis.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("Saved adbe_analysis.html")
