import io

with io.open('scraper/yahoo.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = "**LATEST MARKET INTELLIGENCE**"
replace = """**EARNINGS WATCHOUTS**
• [Bullet 1: Analyze the transcript text provided. Extract the most important future growth guidance, numerical targets, or strategic roadmap explicitly mentioned by management in the latest earnings call.]
• [Bullet 2: Identify a key operational initiative, product launch, or restructuring effort discussed in the recent SEC reports or earnings call.]
• [Bullet 3: Extract a specific warning, headwind, or challenge that management highlighted in the latest quarter.]

**LATEST MARKET INTELLIGENCE**"""

if "**EARNINGS WATCHOUTS**" not in text:
    text = text.replace(target, replace)
    with io.open('scraper/yahoo.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Injected EARNINGS WATCHOUTS into scraper/yahoo.py")
else:
    print("Already exists")
