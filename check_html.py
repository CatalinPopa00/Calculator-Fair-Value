import re
import io

with io.open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

match = re.search(r'(<div class="research-card glass-card" id="ownership-card">.*?<div class="card-body-collapsible">.*?)<div class="research-card', text, re.DOTALL)
if match:
    print(match.group(1)[:2000])
else:
    print("Ownership card not found using regex")

