with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
    backend = f.read()

import re
backend = re.sub(
    r'Act as an expert journalist.*?introductory or concluding fluff\."',
    'Act as an expert journalist: include all key facts, statistics, direct quotes, and the full narrative flow. If you cannot access the exact article due to paywalls, use your search tool to find other reliable news sources reporting on the EXACT SAME EVENT or topic \'{title}\', and write a comprehensive news report about it. Format the response beautifully using HTML <p> tags for paragraphs. Do not use markdown backticks, just output the HTML directly. Do not include introductory or concluding fluff."',
    backend,
    flags=re.DOTALL
)

with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
    f.write(backend)

print("Prompt fixed with regex")
