import re

with open('api/kpi_audit.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_inst = "YOU MUST ACTIVELY USE THE SEARCH TOOL to search 'Nasdaq [ticker] earnings estimates' to fetch the 4+ years of EPS and Revenue estimates directly from the web!"

new_inst = "YOU MUST ACTIVELY USE THE SEARCH TOOL to search '[ticker] earnings estimates 2026 2027 2028' (do NOT restrict the search to Nasdaq, let the search engine find data from SeekingAlpha, WallStreetZen etc) to fetch the multi-year EPS and Revenue estimates directly from the web!"

if old_inst in content:
    content = content.replace(old_inst, new_inst)
    with open('api/kpi_audit.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched instruction 4 successfully.")
else:
    print("Old instruction not found. Content contains:")
    # Print the relevant part to see what it is
    idx = content.find("Our local `Estimates` context")
    if idx != -1:
        print(content[idx:idx+300])
