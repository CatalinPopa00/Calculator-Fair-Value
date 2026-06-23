with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
    backend = f.read()

old_prompt = """prompt = f"Please search the web for the news article titled '{title}' (URL: {url}). Read it carefully and provide a highly detailed, comprehensive summary of the entire article. Act as an expert journalist: include all key facts, statistics, direct quotes, and the full narrative flow. Format the response beautifully using HTML <p> tags for paragraphs. Do not use markdown backticks, just output the HTML directly. Do not include introductory or concluding fluff." """

new_prompt = """prompt = f"Please search the web for the news article titled '{title}' (URL: {url}). Read it carefully and provide a highly detailed, comprehensive summary of the entire article. Act as an expert journalist: include all key facts, statistics, direct quotes, and the full narrative flow. If you cannot access the exact article due to paywalls, use your search tool to find other reliable news sources reporting on the EXACT SAME EVENT or topic '{title}', and write a comprehensive news report about it. Format the response beautifully using HTML <p> tags for paragraphs. Do not use markdown backticks, just output the HTML directly. Do not include introductory or concluding fluff." """

backend = backend.replace(old_prompt, new_prompt)

with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
    f.write(backend)

print("Prompt fallback added")
