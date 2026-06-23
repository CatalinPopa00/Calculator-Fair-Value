with open('index.html', 'r', encoding='utf-8') as f:
    index_html = f.read()

old_btns = """                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <a id="news-modal-bypass-btn" href="#" target="_blank" style="flex: 1; text-align: center; display: flex; justify-content: center; align-items: center; background: #38bdf8; color: white; padding: 12px 20px; border-radius: 8px; font-weight: 700; text-decoration: none; font-size: 0.95rem; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4);">🔓 Bypass Paywall & Read</a>"""

new_btns = """                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <a id="news-modal-read-in-app-btn" href="#" style="flex: 100%; text-align: center; display: flex; justify-content: center; align-items: center; background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); color: white; padding: 12px 20px; border-radius: 8px; font-weight: 700; text-decoration: none; font-size: 0.95rem; box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4); margin-bottom: 5px; transition: all 0.2s;">✨ Read Full Article in App (AI Extract)</a>
                    <a id="news-modal-bypass-btn" href="#" target="_blank" style="flex: 1; text-align: center; display: flex; justify-content: center; align-items: center; background: #38bdf8; color: white; padding: 12px 20px; border-radius: 8px; font-weight: 700; text-decoration: none; font-size: 0.95rem; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4);">🔓 Bypass Paywall & Read</a>"""

index_html = index_html.replace(old_btns, new_btns)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(index_html)
print("index.html updated")
