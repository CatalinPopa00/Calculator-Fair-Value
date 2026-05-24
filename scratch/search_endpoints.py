import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("index.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "@app." in line or "app.mount" in line:
        print(f"Line {idx+1}: {line.strip()}")
