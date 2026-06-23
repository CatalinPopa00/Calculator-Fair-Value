import re

with open('app.js', 'r', encoding='utf-8') as f:
    frontend = f.read()

frontend = frontend.replace("window.addEventListener('resize', updateActiveNavIndicator);", "// window.addEventListener('resize', updateActiveNavIndicator); // Removed undefined function")

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(frontend)

print("Removed updateActiveNavIndicator listener")
