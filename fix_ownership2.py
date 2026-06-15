import re

with open('app.js', 'r') as f:
    js = f.read()

# Fix RHM.DE crashing because chart update fails if the chart hasn't been created yet or is hidden
pattern = r"""(\s*const\s*ctx\s*=\s*document\.getElementById\('roster-pie-chart'\);\s*if\s*\(ctx\)\s*\{\s*if\s*\(window\.rosterPieChart\)\s*window\.rosterPieChart\.destroy\(\);\s*)"""
replacement = r"""\1
                    // Only attempt to render chart if we have data to prevent errors
                    if (data.length === 0) return;
"""

js = re.sub(pattern, replacement, js)

with open('app.js', 'w') as f:
    f.write(js)
