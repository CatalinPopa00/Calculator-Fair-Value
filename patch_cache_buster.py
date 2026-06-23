with open('app.js', 'r', encoding='utf-8') as f:
    frontend = f.read()

import re
frontend = re.sub(
    r'fetch\(`/api/read-article\?title=\$\{encodeURIComponent\(title\)\}&url=\$\{encodeURIComponent\(url\)\}`\)',
    r'fetch(`/api/read-article?title=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}&t=${Date.now()}`)',
    frontend
)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(frontend)

with open('index.html', 'r', encoding='utf-8') as f:
    index = f.read()

index = re.sub(r'app\.js\?v=\d+', 'app.js?v=' + str(import_time()), index)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(index)
