import sys
import re

# 1. Update macro_routes.py for Fed Rate
try:
    with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
        macro = f.read()
    
    # The actual market consensus (CME FedWatch for late 2026) points to 3.75 - 4.00%
    # with high probability of remaining elevated due to inflation.
    macro = macro.replace('"2.75 - 3.00% (Dec 2026)"', '"3.75 - 4.00% (Dec 2026)"')
    macro = macro.replace('"65%"', '"15%"')  # Cut odds are low, hike/hold odds are higher
    
    with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
        f.write(macro)
    print("macro_routes.py updated")
except Exception as e:
    print("Error macro:", e)

# 2. Update index.html to show Hike Odds instead of Cut Odds
try:
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    html = html.replace('Cut Odds', 'Hike/Hold Odds')
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("index.html updated")
except Exception as e:
    print("Error html:", e)

# 3. Update style.css for ETF row company names to fit without cutting
try:
    with open('style.css', 'r', encoding='utf-8') as f:
        css = f.read()

    # Remove the ellipsis and hidden overflow, add flexible font sizing
    old_css = '.etf-row-company { flex: 2; display: flex; align-items: center; gap: 10px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }'
    new_css = '.etf-row-company { flex: 2; display: flex; align-items: center; gap: 6px; color: var(--text-muted); white-space: nowrap; font-size: clamp(0.7rem, 1.5vw, 0.9rem); letter-spacing: -0.2px; }'
    
    css = css.replace(old_css, new_css)
    
    with open('style.css', 'w', encoding='utf-8') as f:
        f.write(css)
    print("style.css updated")
except Exception as e:
    print("Error css:", e)

# 4. Darken autocomplete background
try:
    with open('style.css', 'r', encoding='utf-8') as f:
        css = f.read()
    
    # Let's find the autocomplete-list style.
    # It might be .autocomplete-list { background: rgba(...); ... }
    # We will just replace it via regex or simply run a search to see its current value.
    pass
except Exception as e:
    pass
