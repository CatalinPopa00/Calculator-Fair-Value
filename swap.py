import re

def process():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find Ownership Segment
    own_start = content.find('<!-- 1. Ownership Segment -->')
    ana_start = content.find('<!-- 2. Analyst Consensus Segment -->')
    ana_end = content.find('</section>', ana_start)

    if own_start == -1 or ana_start == -1 or ana_end == -1:
        print("Could not find segments")
        return

    ownership_html = content[own_start:ana_start]
    analyst_html = content[ana_start:ana_end]

    # Modify Ownership
    ownership_html = ownership_html.replace(
        '<div class="research-header">',
        '<div class="research-header card-header" style="margin-bottom: 0;">'
    )
    ownership_html = ownership_html.replace(
        '<h3 class="research-title">Ownership</h3>',
        '''<h3 class="research-title collapsible-trigger" data-card="ownership" style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin: 0; width: 100%;">
                                        Ownership
                                        <svg class="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" style="margin-left: auto;"><polyline points="6 9 12 15 18 9"></polyline></svg>
                                    </h3>
                                </div>
                                <div class="card-body-collapsible" style="padding-top: 1.5rem;">'''
    )
    # The replace above already closed the research-header and opened card-body-collapsible.
    # But wait, original HTML has </div> after the </h3>.
    # Let's check original Ownership HTML:
    # <div class="research-header">
    #     <div class="header-icon">👥</div>
    #     <h3 class="research-title">Ownership</h3>
    # </div>
    # So if I replace the h3 with the new h3 + </div> + <div class="card-body-collapsible">, I should delete the existing </div>.
    
    # Let's do regex instead to be safe.
    own_header_pattern = re.compile(r'(<div class="research-header">.*?<h3 class="research-title">Ownership</h3>\s*</div>)', re.DOTALL)
    
    def own_repl(m):
        orig = m.group(1)
        res = orig.replace('<div class="research-header">', '<div class="research-header card-header" style="margin-bottom: 0;">')
        res = res.replace('<h3 class="research-title">Ownership</h3>', 
                          '<h3 class="research-title collapsible-trigger" data-card="ownership" style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin: 0; width: 100%;">Ownership<svg class="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" style="margin-left: auto;"><polyline points="6 9 12 15 18 9"></polyline></svg></h3>')
        return res + '\n                                <div class="card-body-collapsible" style="padding-top: 1.5rem;">'
        
    ownership_html = own_header_pattern.sub(own_repl, ownership_html)
    
    # Close the card-body-collapsible right before the last </div>
    ownership_html = ownership_html.rstrip()
    if ownership_html.endswith('</div>'):
        ownership_html = ownership_html[:-6] + '</div>\n                            </div>\n'
    else:
        # Fallback if there's trailing whitespace
        ownership_html = re.sub(r'</div>\s*$', '</div>\n                            </div>\n', ownership_html)

    # Modify Analyst
    ana_header_pattern = re.compile(r'(<div class="research-header">.*?<h3 class="research-title">Analyst Consensus & Projections</h3>\s*</div>)', re.DOTALL)
    
    def ana_repl(m):
        orig = m.group(1)
        res = orig.replace('<div class="research-header">', '<div class="research-header card-header" style="margin-bottom: 0;">')
        res = res.replace('<h3 class="research-title">Analyst Consensus & Projections</h3>', 
                          '<h3 class="research-title collapsible-trigger" data-card="analyst-estimates" style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin: 0; width: 100%;">Analyst Consensus & Projections<svg class="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" style="margin-left: auto;"><polyline points="6 9 12 15 18 9"></polyline></svg></h3>')
        return res + '\n                                <div class="card-body-collapsible" style="padding-top: 1.5rem;">'
        
    analyst_html = ana_header_pattern.sub(ana_repl, analyst_html)
    
    analyst_html = analyst_html.rstrip()
    if analyst_html.endswith('</div>'):
        analyst_html = analyst_html[:-6] + '</div>\n                            </div>\n'
    else:
        analyst_html = re.sub(r'</div>\s*$', '</div>\n                            </div>\n', analyst_html)

    # Swap
    new_content = content[:own_start] + analyst_html + '\n                            ' + ownership_html + content[ana_end:]

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Successfully swapped and added collapsible!")

process()
