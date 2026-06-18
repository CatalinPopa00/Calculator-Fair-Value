from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://www.wsj.com/articles/a-great-stock-market-rally-meets-a-big-bump-f6110f27"
try:
    response = requests.get(url, impersonate="chrome110", timeout=15)
    print("Status:", response.status_code)
    soup = BeautifulSoup(response.content, "html.parser")
    article = soup.find("article") or soup.find("main") or soup.find("div", class_="article-body") or soup.find("div", class_="story")
    if article:
        ps = article.find_all("p")
        print(f"Found {len(ps)} paragraphs")
        print(ps[0].get_text() if ps else "No paragraphs")
    else:
        print("No article container found")
        print(response.text[:500])
except Exception as e:
    print("Error:", e)
