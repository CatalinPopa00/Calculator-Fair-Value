import re

with open("adbe_analysis.html", "r", encoding="utf-8") as f:
    content = f.read()

# Find all occurrences of yearAgoEps
matches = re.finditer(r'("period":"([\+0]y)".*?"yearAgoEps":\{"raw":([\d\.\-]+))', content)
for m in matches:
    print(f"Match: {m.group(1)} (Period: {m.group(2)}, Value: {m.group(3)})")

# Try different order
matches2 = re.finditer(r'("yearAgoEps":\{"raw":([\d\.\-]+).*?"period":"([\+0]y)")', content)
for m in matches2:
    print(f"Match Reverse: {m.group(1)} (Period: {m.group(3)}, Value: {m.group(2)})")
