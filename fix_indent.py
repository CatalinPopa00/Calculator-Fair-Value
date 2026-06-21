import sys

try:
    with open('scraper/yahoo.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    start_idx = -1
    end_idx = -1
    for i, line in enumerate(lines):
        if '# --- PHASE 3: QUARTERLY ANCHORS ---' in line:
            start_idx = i
        if '# Final return object' in line:
            end_idx = i

    if start_idx != -1 and end_idx != -1:
        for i in range(start_idx, end_idx):
            if lines[i].startswith('            '): # 12 spaces
                lines[i] = lines[i][4:]
            elif lines[i].startswith('        ') and lines[i].strip() == '':
                lines[i] = '\n'

        with open('scraper/yahoo.py', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print('Fixed indentation')
except Exception as e:
    print('Error:', e)
