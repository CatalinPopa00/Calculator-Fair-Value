import os

filepath = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value\app.js"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("s.metric.split(' (')[0]", "s.metric")
content = content.replace("r.metric.split(' (')[0]", "r.metric")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Removed .split(' (')[0] from app.js")
