import os
import re

with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

# 1. Remove Mobile Bottom Nav Auto-Hide
auto_hide_pattern = re.compile(r'// Mobile Bottom Nav Auto-Hide.*?}\);', re.DOTALL)
app_js = auto_hide_pattern.sub('', app_js)

# 2. Add resize listener for nav indicator
if "window.addEventListener('resize', updateActiveNavIndicator);" not in app_js:
    # Find updateActiveNavIndicator function definition and insert after
    if "function updateActiveNavIndicator" in app_js:
        app_js = app_js.replace(
            "function updateActiveNavIndicator",
            "window.addEventListener('resize', updateActiveNavIndicator);\n    function updateActiveNavIndicator"
        )
    else:
        app_js += "\nwindow.addEventListener('resize', updateActiveNavIndicator);\n"

# 3. Fix WSJ Bypass and Layout
# We replace the old card HTML and bypass logic
wsj_old_bypass = "const bypassUrl = `/api/article-bypass?url=${encodeURIComponent(link)}`;"
wsj_new_bypass = "const bypassUrl = `https://www.removepaywall.com/search?url=${encodeURIComponent(link)}`;"
app_js = app_js.replace(wsj_old_bypass, wsj_new_bypass)

# Change the WSJ card styling to look better without images
wsj_old_img = "const imgHtml = `<div class=\"news-img wsj-img\" style=\"font-size:3rem; background: #0f172a; color: white; display:flex; align-items:center; justify-content:center; border-bottom: 1px solid var(--border);\">WSJ</div>`;"
wsj_new_img = """const imgHtml = `<div class="news-img wsj-img" style="font-size:2.5rem; background: radial-gradient(circle, #1e293b 0%, #0f172a 100%); color: rgba(255,255,255,0.8); display:flex; align-items:center; justify-content:center; border-bottom: 1px solid var(--border); font-family: serif; font-style: italic; font-weight: bold; letter-spacing: 2px;">WSJ.</div>`;"""
app_js = app_js.replace(wsj_old_img, wsj_new_img)

# 4. Tooltip Scroll Issue (Prevent it from hiding constantly when hovering near scrollable areas)
# Let's just comment out the scroll listener for tipsTooltip
scroll_hide_pattern = re.compile(r'customScenariosModalContent\.addEventListener\(\'scroll\', \(\) => \{\s*if \(tipsTooltip\.style\.display === \'block\'\) \{\s*tipsTooltip\.style\.display = \'none\';\s*\}\s*\}\);', re.DOTALL)
app_js = scroll_hide_pattern.sub('// Tooltip scroll hide disabled to prevent glitching', app_js)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)

# --- INDEX.HTML FIXES ---
with open('index.html', 'r', encoding='utf-8') as f:
    index_html = f.read()

# 5. Fix Favicon 404 for Russell 2000 and DAX (and Nasdaq just in case)
# Replace google s2 favicons with direct UI avatars to avoid 404s in console
index_html = index_html.replace('src="https://www.google.com/s2/favicons?sz=64&domain=ftserussell.com"', 'src="https://ui-avatars.com/api/?name=R2&background=0f172a&color=fff"')
index_html = index_html.replace('src="https://www.google.com/s2/favicons?sz=64&domain=nasdaq.com"', 'src="https://ui-avatars.com/api/?name=NQ&background=0f172a&color=fff"')
index_html = index_html.replace('src="https://www.google.com/s2/favicons?sz=64&domain=deutsche-boerse.com"', 'src="https://ui-avatars.com/api/?name=DX&background=0f172a&color=fff"')
index_html = index_html.replace('src="https://www.google.com/s2/favicons?sz=64&domain=spglobal.com"', 'src="https://ui-avatars.com/api/?name=DJ&background=0f172a&color=fff"')

# 6. Fix Tooltip Z-Index
index_html = index_html.replace('z-index: 10010;', 'z-index: 20000; pointer-events: none;')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(index_html)

print("UI Bugs Patched")
