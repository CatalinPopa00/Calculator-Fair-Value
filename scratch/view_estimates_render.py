import sys
sys.stdout.reconfigure(encoding='utf-8')

def print_range(filepath, start_line, end_line):
    print(f"=== {filepath} ({start_line} to {end_line}) ===")
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for idx in range(start_line - 1, min(end_line, len(lines))):
        print(f"{idx+1}: {lines[idx]}", end="")

print_range("app.js", 2800, 2860)
