import re
import io

with io.open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

match = re.search(r'<h3.*?data-card=\"ownership\".*?</h3>(.*?)(?=<div class=\"research-card)', text, re.DOTALL)
if match:
    print(match.group(1)[:2000])
else:
    print("Not found")
