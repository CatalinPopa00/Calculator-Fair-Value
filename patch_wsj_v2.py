import re

with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
    backend = f.read()

# 1. Update WSJ RSS feed
backend = backend.replace(
    "r = requests.get('https://feeds.a.dj.com/rss/RSSMarketsMain.xml', headers=headers, timeout=10)",
    "r = requests.get('https://news.google.com/rss/search?q=site:wsj.com+when:7d', headers=headers, timeout=8)"
)

# 2. Update timeout in read_article to 8s (Vercel limit is 10s)
backend = backend.replace(
    "timeout=15",
    "timeout=8"
)

with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
    f.write(backend)


with open('app.js', 'r', encoding='utf-8') as f:
    frontend = f.read()

# 3. Fix WSJ card UI (remove ugly big block, make it look clean)
old_img = """const imgHtml = `<div class="news-img wsj-img" style="font-size:2.5rem; background: radial-gradient(circle, #1e293b 0%, #0f172a 100%); color: rgba(255,255,255,0.8); display:flex; align-items:center; justify-content:center; border-bottom: 1px solid var(--border); font-family: serif; font-style: italic; font-weight: bold; letter-spacing: 2px;">WSJ.</div>`;"""
new_img = """const imgHtml = ''; // Removed big block based on user feedback"""
frontend = frontend.replace(old_img, new_img)

# Fix the innerHTML of WSJ card to have WSJ badge and date inline
old_card_inner = """
                ${imgHtml}
                <div class="news-content">
                    <div class="news-title">${title}</div>
                    <div class="news-meta">
                        <span class="news-source">Wall Street Journal</span>
                        <span class="news-date">${date}</span>
                    </div>
                </div>
"""
new_card_inner = """
                ${imgHtml}
                <div class="news-content" style="padding: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 5px;">
                        <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 0.7rem; padding: 4px 8px; border-radius: 6px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; font-family: serif; font-style: italic;">WSJ.</span>
                        <span class="news-date" style="font-size: 0.75rem; color: rgba(255,255,255,0.45); font-weight: 500;">${date}</span>
                    </div>
                    <div class="news-title" style="font-size: 0.95rem; line-height: 1.4;">${title}</div>
                </div>
"""
frontend = frontend.replace(old_card_inner, new_card_inner)

# 4. Improve error logging in JS
old_error = """alert("Eroare la extragerea articolului: " + (data.error || "Unknown error"));"""
new_error = """
                        let errMsg = data.error || data.detail || data.message || "Unknown error";
                        if (typeof errMsg === 'object') errMsg = JSON.stringify(errMsg);
                        if (errMsg === "Unknown error" && !data.error) errMsg = "Unknown error: " + JSON.stringify(data);
                        alert("Eroare la extragerea articolului: " + errMsg);
"""
frontend = frontend.replace(old_error, new_error)

# Also fix the pubDate extraction for Google News RSS (it uses pubDate, same as old RSS)
# It's already item.find('pubDate').text

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(frontend)

print("Patch applied")
