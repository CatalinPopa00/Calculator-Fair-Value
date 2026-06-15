import io

with io.open('scraper/yahoo.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.startswith('    output += f"**EARNINGS WATCHOUTS**'):
        skip = True
        # add the correct fixed line
        new_lines.append('    output += f"**EARNINGS WATCHOUTS**\\n" + "\\n".join(["• Loading AI watchouts..."]) + "\\n\\n"\n')
        new_lines.append('    output += f"**LATEST MARKET INTELLIGENCE**\\n" + "\\n".join([f"• {n}" for n in fallback_news])\n')
        continue
    
    if skip:
        if line.startswith('**LATEST MARKET INTELLIGENCE**\\n" + "\\n".join([f"• {n}" for n in fallback_news])'):
            skip = False
        continue

    new_lines.append(line)

with io.open('scraper/yahoo.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
    
print("Fixed syntax error in scraper/yahoo.py")
