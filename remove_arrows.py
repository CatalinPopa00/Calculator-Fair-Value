import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove the mobile-carousel-nav-absolute div and all its contents
text = re.sub(r'<div class="mobile-carousel-nav-absolute".*?</div>', '', text, flags=re.DOTALL)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Removed arrows")
