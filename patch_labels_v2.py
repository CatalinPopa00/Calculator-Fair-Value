import sys
import re

files = [
    r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\Calculator-Fair-Value\app.js',
    r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\Calculator-Fair-Value\vercel_app_v234.js'
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # We want to replace whatever the LABEL is with the strictly requested format
    # The current one looks like: const LABEL = { PE: 'FWD P/E', PFCF: 'Trailing P/FCF', PS: 'FWD P/S', PB: 'Current P/B', EV_EBITDA: 'FWD EV/EBITDA', P_FFO: 'FWD P/FFO', P_AFFO: 'FWD P/AFFO' };
    # Let's use regex to replace it
    new_label = "const LABEL = { PE: 'FWD P/E', PFCF: 'P/FCF', PS: 'FWD P/S', PB: 'P/B', EV_EBITDA: 'FWD EV/EBITDA', P_FFO: 'FWD P/FFO', P_AFFO: 'FWD P/AFFO' };"
    
    content = re.sub(r"const LABEL = \{.*?\};", new_label, content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {filepath}")
