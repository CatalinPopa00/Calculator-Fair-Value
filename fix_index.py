import re

with open('index.html', 'r') as f:
    html = f.read()

# Remove old button location
pattern1 = r'\s*<button id="theme-toggle-btn"[^>]*>🌞</button>'
html = re.sub(pattern1, '', html)

# Add new button location fixed to bottom left
pattern2 = r'(</body>)'
replacement2 = r"""    <button id="theme-toggle-btn" class="theme-toggle" title="Toggle Theme" style="position: fixed; bottom: 20px; left: 20px; z-index: 9999; background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 50%; font-size: 1.5rem; cursor: pointer; padding: 0.5rem; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.3s, background-color 0.3s;">🌞</button>
\1"""
html = re.sub(pattern2, replacement2, html)

with open('index.html', 'w') as f:
    f.write(html)
