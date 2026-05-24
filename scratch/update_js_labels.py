import os
import re

js_files = ['app.js', 'vercel_app.js', 'vercel_app_v234.js']

for filename in js_files:
    filepath = os.path.join(r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value", filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Replace metric.includes('EV / EBITDA') with metric.includes('EV/EBITDA') || metric.includes('EV / EBITDA')
    content = content.replace("metric.includes('EV / EBITDA')", "(metric.includes('EV/EBITDA') || metric.includes('EV / EBITDA'))")
    
    # We should also check P/AFFO
    content = content.replace("metric.includes('P/AFFO')", "(metric.includes('P/AFFO') || metric.includes('P/AFFO'))") # just to be safe, it's already there
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated JS logic in {filename}")
