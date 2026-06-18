import requests
from bs4 import BeautifulSoup

url = "https://www.wsj.com/articles/a-great-stock-market-rally-meets-a-big-bump-f6110f27"
headers = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Referer": "https://www.google.com/"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(response.status_code)
    soup = BeautifulSoup(response.content, "html.parser")
    print(soup.find("title").get_text() if soup.find("title") else "No title")
    article = soup.find("article") or soup.find("main") or soup.find("div", class_="article-body") or soup.find("div", class_="story")
    if article:
        ps = article.find_all("p")
        print(f"Found {len(ps)} paragraphs")
        print(ps[0].get_text() if ps else "No paragraphs")
    else:
        print("No article container found")
except Exception as e:
    print(e)
