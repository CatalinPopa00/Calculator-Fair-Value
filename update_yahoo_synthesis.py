import io
import re

def update_yahoo():
    with io.open('scraper/yahoo.py', 'r', encoding='utf-8') as f:
        text = f.read()

    # Add import
    if 'from api.kpi_audit import get_fmp_transcripts' not in text:
        text = text.replace('import requests\n', 'import requests\nfrom api.kpi_audit import get_fmp_transcripts\n')

    # Add get_fmp_transcripts call and add it to the prompt context
    target_prompt_start = "    if run_ai:\n        api_key = load_gemini_api_key()\n        if api_key:\n            # Fetch news first (only when running AI)"
    replace_prompt_start = """    if run_ai:
        api_key = load_gemini_api_key()
        if api_key:
            # Fetch transcripts
            try:
                transcript_text = get_fmp_transcripts(ticker_upper)
                # truncate to ~60000 chars to avoid prompt blowing up and taking forever
                if transcript_text and len(transcript_text) > 60000:
                    transcript_text = transcript_text[:60000]
            except Exception as e:
                print(f"Error fetching transcripts for synthesis: {e}")
                transcript_text = "No transcript data available."

            # Fetch news first (only when running AI)"""

    if 'transcript_text = get_fmp_transcripts(ticker_upper)' not in text:
        text = text.replace(target_prompt_start, replace_prompt_start)

    # Update the prompt text to include transcripts and earnings watchouts
    target_prompt_content = """LATEST NEWS AND MARKET EVENTS:
{news_text}

Provide a highly professional,"""

    replace_prompt_content = """LATEST NEWS AND MARKET EVENTS:
{news_text}

LATEST EARNINGS TRANSCRIPTS & SEC REPORTS:
{transcript_text}

Provide a highly professional,"""

    if 'LATEST EARNINGS TRANSCRIPTS' not in text:
        text = text.replace(target_prompt_content, replace_prompt_content)


    target_prompt_format = """**LATEST MARKET INTELLIGENCE**
 [Translate the first relevant news into English (Source: Publication Name)"""

    replace_prompt_format = """**EARNINGS WATCHOUTS**
 [Bullet 1: Analyze the transcript text provided. Extract the most important future growth guidance, numerical targets, or strategic roadmap explicitly mentioned by management in the latest earnings call.]
 [Bullet 2: Identify a key operational initiative, product launch, or restructuring effort discussed in the recent SEC reports or earnings call.]
 [Bullet 3: Extract a specific warning, headwind, or challenge that management highlighted in the latest quarter.]

**LATEST MARKET INTELLIGENCE**
 [Translate the first relevant news into English (Source: Publication Name)"""

    if '**EARNINGS WATCHOUTS**' not in text:
        text = text.replace(target_prompt_format, replace_prompt_format)

    with io.open('scraper/yahoo.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Updated scraper/yahoo.py")

update_yahoo()
