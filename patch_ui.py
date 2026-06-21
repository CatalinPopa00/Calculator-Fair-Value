import re

try:
    with open('style.css', 'r', encoding='utf-8') as f:
        css = f.read()
    
    # 1. CSS for search-loading-active
    glow_css = """
@keyframes borderGlow {
    0% { box-shadow: 0 0 5px var(--primary); border-color: var(--primary); }
    50% { box-shadow: 0 0 20px var(--primary); border-color: var(--primary); }
    100% { box-shadow: 0 0 5px var(--primary); border-color: var(--primary); }
}
.search-loading-active {
    animation: borderGlow 1.5s infinite ease-in-out !important;
    border-color: var(--primary) !important;
}
"""
    if "borderGlow" not in css:
        css += glow_css

    # 2. Fix mobile autocomplete dropdown width
    # In the media query max-width: 768px, we can add this. We'll just append it at the end.
    mobile_fix = """
@media (max-width: 768px) {
    .search-glass-popup .autocomplete-dropdown {
        width: calc(100% + 115px + 0.5rem) !important;
        max-width: none;
    }
}
"""
    if "calc(100% + 115px + 0.5rem)" not in css:
        css += mobile_fix

    # 3. Center search bar (if it was pushed right, maybe padding inside popup was wrong or margin)
    # Just add a general fix for search-container inside popup
    center_fix = """
.search-glass-popup .search-container {
    justify-content: center;
    margin: 0 auto;
}
"""
    if "justify-content: center" not in css:
        css += center_fix
        
    with open('style.css', 'w', encoding='utf-8') as f:
        f.write(css)
    print("style.css patched.")

    # HTML Patch: Remove Fed Rate Forecast
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    html = re.sub(r'<div style="display: flex; justify-content: space-between; margin-bottom: 8px; align-items: center;">\s*<span style="color: var\(--text-muted\);">Forecast</span>\s*<span style="font-weight: 600; color: var\(--accent\);" id="fed-forecast">--</span>\s*</div>', '', html)
    html = re.sub(r'<div style="display: flex; justify-content: space-between;">\s*<span style="color: var\(--text-muted\);">Cut Odds</span>\s*<span style="font-weight: 600; color: #10b981;" id="fed-prob">--</span>\s*</div>', '', html)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("index.html patched.")

    # API Patch: Remove Fed Rate Forecast from macro_routes.py
    with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
        api_py = f.read()
    
    api_py = re.sub(r'"forecast": "[^"]+",\n\s*"cut_probability": "[^"]+",\n\s*"hike_probability": "[^"]+"', '"forecast": "",\n                                "cut_probability": "",\n                                "hike_probability": ""', api_py)

    with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
        f.write(api_py)
    print("macro_routes.py patched.")

except Exception as e:
    print("Error:", e)
