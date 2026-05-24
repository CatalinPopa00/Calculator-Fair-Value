import re
with open('index.html', encoding='utf-8') as f:
    text = f.read()
ids = re.findall(r'id="([^"]+)"', text)
dups = set(x for x in ids if ids.count(x) > 1)
print("Duplicates:", dups)
