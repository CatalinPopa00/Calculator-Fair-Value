import os

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Fix the missing closing tags for historical-charts-section
html = html.replace('</div>\n                                    </div>\n\n                        <!-- DEEP RESEARCH', '</div>\n                                    </div>\n                                </div>\n                            </section>\n\n                        <!-- DEEP RESEARCH')

# Extract Analyst Consensus
analyst_start = html.find('<!-- 2. Analyst Consensus Segment -->')
hist_start = html.find('<!-- 2. Historical Trends Segment -->')
analyst_html = html[analyst_start:hist_start]

# Extract Historical Trends Segment
own_start = html.find('<!-- 1. Ownership Segment -->')
hist_html = html[hist_start:own_start]

# Extract Ownership Segment
own_end = html.find('</section>\n\n                        <div style="text-align: center; margin-top: 3rem;')
if own_end == -1:
    own_end = html.find('</section>\n\n                        <div style="text-align: center;')
own_html = html[own_start:own_end]

# Fix Ownership collapsibility
own_html = own_html.replace(
    '<div class="card-body-collapsible" style="padding-top: 1.5rem;">\n                                </div>',
    '<div class="card-body-collapsible" style="padding-top: 1.5rem;">'
)
# Add closing div for card-body-collapsible at the end of ownership
own_html = own_html.rstrip()
if own_html.endswith('</div>'):
    own_html = own_html[:-6] + '</div>\n                                </div>\n                            </div>\n'

# Fix Historical Trends collapsibility
hist_html = hist_html.replace(
    '<div class="research-header">\n                                    <div class="header-icon">⏳</div>\n                                    <h3 class="research-title">Historical Anchors & Trends</h3>\n                                </div>',
    '<div class="research-header card-header" style="margin-bottom: 0;">\n                                    <div class="header-icon">⏳</div>\n                                    <h3 class="research-title collapsible-trigger" data-card="historical-anchors" style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin: 0; width: 100%;">\n                                        Historical Anchors & Trends\n                                        <svg class="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" style="margin-left: auto;"><polyline points="6 9 12 15 18 9"></polyline></svg>\n                                    </h3>\n                                </div>\n                                <div class="card-body-collapsible" style="padding-top: 1.5rem;">'
)
hist_html = hist_html.replace(
    '<div class="research-footer">\n                                    * EPS values represent Diluted EPS (GAAP) for historical accuracy.\n                                </div>\n                            </div>\n                            </div>',
    '<div class="research-footer">\n                                    * EPS values represent Diluted EPS (GAAP) for historical accuracy.\n                                </div>\n                                </div>\n                            </div>\n'
)

# Combine in the new order: Analyst -> Ownership -> Historical
new_deep_research = analyst_html + '\n' + own_html + '\n' + hist_html + '\n'

# Replace in the main html
html = html[:analyst_start] + new_deep_research + html[own_end:]

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Fix applied successfully")
