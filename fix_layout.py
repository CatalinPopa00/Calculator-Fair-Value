import sys
import re

# 1. Fix style.css
try:
    with open('style.css', 'r', encoding='utf-8') as f:
        css = f.read()
    
    # Change flex-direction to row, add align-items center and gap
    css = re.sub(
        r'\.etf-header h4\s*\{\s*margin:\s*0;\s*font-size:\s*1\.2rem;\s*font-weight:\s*700;\s*display:\s*flex;\s*flex-direction:\s*column;\s*\}',
        '.etf-header h4 { margin: 0; font-size: 1.1rem; font-weight: 700; display: flex; flex-direction: row; align-items: baseline; gap: 8px; flex-wrap: wrap; }',
        css
    )
    
    # Make live-price a bit smaller and remove margin-top
    css = re.sub(
        r'\.etf-header h4 \.live-price\s*\{\s*font-size:\s*0\.85rem;\s*font-weight:\s*500;\s*margin-top:\s*2px;\s*\}',
        '.etf-header h4 .live-price { font-size: 0.9rem; font-weight: 500; margin-top: 0; }',
        css
    )

    with open('style.css', 'w', encoding='utf-8') as f:
        f.write(css)
    print('style.css fixed')
except Exception as e:
    print('Error css:', e)

# 2. Fix index.html
try:
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # Fix the nested div for Fed Rate
    bad_html = '''                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                      <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                          <span style="color: var(--text-muted);">Forecast</span>
                          <span style="font-weight: 600; color: #fbbf24; white-space: nowrap; font-size: 0.95em;" id="fed-forecast">--</span>
                      </div>
                    </div>'''
                    
    good_html = '''                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; align-items: center;">
                        <span style="color: var(--text-muted); margin-right: 10px;">Forecast</span>
                        <span style="font-weight: 600; color: #fbbf24; white-space: nowrap; font-size: 0.9em; text-align: right;" id="fed-forecast">--</span>
                    </div>'''

    html = html.replace(bad_html, good_html)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('index.html fixed')
except Exception as e:
    print('Error html:', e)
