import sys
sys.stdout.reconfigure(encoding='utf-8')

def search_keywords(filepath, keywords):
    print(f"=== {filepath} ===")
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for idx, line in enumerate(lines):
        for kw in keywords:
            if kw in line:
                print(f"Line {idx+1}: {line.strip()[:120]}")

search_keywords("index.py", ["revenue", "growth", "estimates"])
search_keywords("app.js", ["revenue", "growth", "estimates"])
