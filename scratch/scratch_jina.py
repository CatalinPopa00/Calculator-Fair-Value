import requests

url = "https://www.wsj.com/articles/a-great-stock-market-rally-meets-a-big-bump-f6110f27"
jina_url = f"https://r.jina.ai/{url}"

try:
    response = requests.get(jina_url, timeout=15)
    print(response.status_code)
    print(response.text[:500])
except Exception as e:
    print(e)
