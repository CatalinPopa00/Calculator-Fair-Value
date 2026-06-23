import re

with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_route = """
import xml.etree.ElementTree as ET
import html

@router.get("/wsj-news")
@safe_cached(cache=TTLCache(maxsize=1, ttl=300), fallback_value={"news": []})
def get_wsj_news():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        # 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml' or 'https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml'
        r = requests.get('https://feeds.a.dj.com/rss/RSSMarketsMain.xml', headers=headers, timeout=10)
        
        root = ET.fromstring(r.content)
        news_items = []
        
        for item in root.findall('./channel/item'):
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            if title and link:
                news_items.append({
                    "title": html.unescape(title),
                    "link": link,
                    "publisher": "Wall Street Journal",
                    "providerPublishTime": pub_date
                })
        
        return {"news": news_items[:15]}
    except Exception as e:
        print(f"Error fetching WSJ news: {e}")
        return {"news": []}
"""

if "def get_wsj_news():" not in content:
    content += "\n" + new_route
    with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added /wsj-news route to macro_routes.py")
else:
    print("WSJ news route already exists")
