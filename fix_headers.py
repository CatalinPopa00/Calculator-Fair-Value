import io
import re

with io.open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Fix Analyst Consensus chevron & alignment
# The card ID is 'analyst-estimates-card'. We need to make sure data-card="analyst-estimates" on triggers so it toggles correctly.
# Or just rename the ID to 'analyst-card' which is safer.
text = text.replace('id="analyst-estimates-card"', 'id="analyst-card"')

# Find Analyst Consensus Title and add justify-content: flex-start
target_analyst = '<h3 class="research-title collapsible-trigger" data-card="analyst" style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin: 0; flex: 1;">'
replace_analyst = '<h3 class="research-title collapsible-trigger" data-card="analyst" style="display: flex; align-items: center; justify-content: flex-start; gap: 10px; cursor: pointer; margin: 0; flex: 1;">'
text = text.replace(target_analyst, replace_analyst)

# 2. Fix Ownership alignment
target_owner = '<h3 class="research-title collapsible-trigger" data-card="ownership" style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin: 0; flex: 1;">'
replace_owner = '<h3 class="research-title collapsible-trigger" data-card="ownership" style="display: flex; align-items: center; justify-content: flex-start; gap: 10px; cursor: pointer; margin: 0; flex: 1;">'
text = text.replace(target_owner, replace_owner)

# 3. Refactor Historical Anchors Header
# We need to replace the entire header structure for Historical Anchors
# Let's find it using regex
hist_pattern = r'(<div class="research-card glass-card" id="historical-anchors-card">\s*)<div class="research-header card-header" style="margin-bottom: 0; display: flex; flex-direction: column; gap: 15px; align-items: stretch;">\s*<div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">\s*<h3 class="research-title collapsible-trigger" data-card="historical-anchors" style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin: 0; width: 100%;">\s*<div class="header-icon">⏳</div>\s*Historical Anchors & Trends\s*</h3>\s*<svg class="chevron-icon collapsible-trigger" data-card="historical-anchors" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" style="cursor:pointer;"><polyline points="6 9 12 15 18 9"></polyline></svg>\s*</div>\s*(<div class="hist-toggle-wrapper".*?</div>\s*</div>)'

def replace_hist(match):
    prefix = match.group(1)
    toggle_wrapper_with_end_div = match.group(2)
    
    # We need to extract the toggle wrapper html without the final </div> that closed the research-header
    # The toggle_wrapper_with_end_div contains: <div class="hist-toggle-wrapper"...>...</div></div>
    # Let's just do a simple replacement of the whole block using the exact toggle wrapper we know exists.
    pass

# Better approach for Historical Anchors:
# I know the exact HTML of the toggle wrapper. I can construct the new header directly.
# Let's find the card start:
split_hist = text.split('id="historical-anchors-card">')
if len(split_hist) == 2:
    # Now find the end of the research-header
    # It contains "hist-toggle-wrapper"
    header_end_idx = split_hist[1].find('<!-- Historical Data Container -->')
    if header_end_idx == -1:
        # try finding another marker
        header_end_idx = split_hist[1].find('<div class="card-body-collapsible"')
        
    if header_end_idx != -1:
        old_header = split_hist[1][:header_end_idx]
        
        # Extract the toggle wrapper
        toggle_match = re.search(r'<div class="hist-toggle-wrapper".*?</div>\s*</div>', old_header, re.DOTALL)
        if toggle_match:
            toggle_html = toggle_match.group(0)
            # Remove the last </div> which belonged to the research-header
            toggle_html = toggle_html.rsplit('</div>', 1)[0].strip()
            
            new_header = """
<div class="research-header card-header historical-header" style="margin-bottom: 0;">
    <h3 class="research-title collapsible-trigger" data-card="historical-anchors" style="display: flex; align-items: center; justify-content: flex-start; gap: 10px; cursor: pointer; margin: 0;">
        <div class="header-icon">⏳</div>
        Historical Anchors & Trends
    </h3>
    
    """ + toggle_html + """
    
    <svg class="chevron-icon collapsible-trigger" data-card="historical-anchors" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" style="cursor:pointer;"><polyline points="6 9 12 15 18 9"></polyline></svg>
</div>
"""
            text = split_hist[0] + 'id="historical-anchors-card">\n' + new_header + split_hist[1][header_end_idx:]

with io.open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Applied HTML fixes successfully.")
