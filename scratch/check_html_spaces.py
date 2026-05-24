import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "peg-eps-source" in line:
        print(f"Line {idx+1}: {repr(line)}")
        print(f"Line {idx+2}: {repr(lines[idx+1])}")
        print(f"Line {idx+3}: {repr(lines[idx+2])}")
