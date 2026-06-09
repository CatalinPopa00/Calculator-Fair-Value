import re

with open('style.css', 'r') as f:
    css = f.read()

# Remove the old flex definition
css = re.sub(r'\.name-watchlist-row \{\s*display: flex;\s*align-items: center;\s*gap: 0\.8rem;\s*\}', '', css)

# Make ticker even larger and bolder
css = re.sub(r'\.ticker-col \.ticker \{\s*font-size: 1\.3rem;\s*font-weight: bold;\s*\}',
             '.ticker-col .ticker {\n    font-size: 2rem;\n    font-weight: 900;\n}', css)

with open('style.css', 'w') as f:
    f.write(css)
