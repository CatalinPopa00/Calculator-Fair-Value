with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
    backend = f.read()

old_prompt = 'prompt = f"I need to extract the full text of the following news article. Title: \'{title}\'. URL: {url}. Please search the web for this article title or content, and provide the FULL TEXT of the article. Do not include introductory text, just return the article content formatted with paragraphs."'

new_prompt = 'prompt = f"Please search the web for the news article titled \'{title}\' (URL: {url}). Read it carefully and provide a highly detailed, comprehensive summary of the entire article. Act as an expert journalist: include all key facts, statistics, direct quotes, and the full narrative flow. Format the response beautifully using HTML <p> tags for paragraphs. Do not use markdown backticks, just output the HTML directly. Do not include introductory or concluding fluff."'

backend = backend.replace(old_prompt, new_prompt)

# Let's also make sure we clean up Markdown ```html blocks if it returns them
old_cleanup = "# Clean up the output if Gemini wraps it in markdown blockquotes or introduces it"
new_cleanup = """
            if content.startswith('```html'): content = content[7:]
            if content.startswith('```'): content = content[3:]
            if content.endswith('```'): content = content[:-3]
            content = content.strip()
"""

backend = backend.replace(old_cleanup, new_cleanup)

with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
    f.write(backend)

print("Prompt updated")
