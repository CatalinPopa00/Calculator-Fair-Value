with open('vercel_app_v234.js', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("'" + chr(8212) + "'", "'null'")

with open('vercel_app_v234.js', 'w', encoding='utf-8') as f:
    f.write(content)
