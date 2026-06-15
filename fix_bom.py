import io

with io.open('scraper/yahoo.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'key_name = k.strip()'
replace = 'key_name = k.strip().lstrip("\\ufeff")'

if replace not in text:
    text = text.replace(target, replace)
    with io.open('scraper/yahoo.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Fixed BOM issue in scraper/yahoo.py")
else:
    print("Already fixed")
