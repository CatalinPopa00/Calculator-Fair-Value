import re

with open('style.css', 'r') as f:
    css = f.read()

# Make light mode text readable and set background correctly
css = css.replace('--bg-dark: #f8fafc;', '--bg-dark: #f0f2f5;')
css = css.replace('--card-bg: rgba(255, 255, 255, 0.9);', '--card-bg: #ffffff;')
css = css.replace('--text-main: #0f172a;', '--text-main: #111827;')
css = css.replace('--text-muted: #64748b;', '--text-muted: #4b5563;')
css = css.replace('--accent: #059669;', '--accent: #059669;')
css = css.replace('--danger: #dc2626;', '--danger: #dc2626;')

with open('style.css', 'w') as f:
    f.write(css)
