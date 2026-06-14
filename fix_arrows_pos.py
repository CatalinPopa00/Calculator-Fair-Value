import io
import re

with io.open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# We want to find:
# <div class="mobile-carousel-nav" ...> ... </div>
# And remove it.
nav_pattern = r'<div class="mobile-carousel-nav".*?</div>\s*'
# Wait, dotall is needed for the buttons inside.
nav_pattern_compiled = re.compile(r'<div class="mobile-carousel-nav" style="display: none; align-items: center; gap: 10px; margin-right: 15px;">.*?</div>\s*', re.DOTALL)

# But wait, instead of removing it and trying to inject into card-body-collapsible, 
# I can just change its CSS to be absolute, 100% width, top 50%, flex with space-between!
# Let's think: if mobile-carousel-nav is inside .research-card, we can position it absolute, width: 100%, left: 0, top: 50% (or top: 150px depending on where the pie chart is).
# Actually, if we put it inside `.card-body-collapsible`, top: 50% will be perfectly centered vertically relative to the body!
# So let's extract the buttons from mobile-carousel-nav, delete mobile-carousel-nav, and inject the buttons at the start of `.card-body-collapsible`.

# For Analyst Consensus Segment
analyst_split = text.split('id="analyst-estimates-card">')
if len(analyst_split) == 2:
    part2 = analyst_split[1]
    # Remove mobile-carousel-nav
    part2 = re.sub(r'<div class="mobile-carousel-nav".*?</div>', '', part2, count=1, flags=re.DOTALL)
    
    # Inject buttons into card-body-collapsible
    buttons = """
<div class="mobile-carousel-nav-absolute" style="display: none; position: absolute; top: 55%; left: 0; width: 100%; justify-content: space-between; padding: 0 5px; z-index: 10; pointer-events: none;">
    <button class="mobile-prev-btn" onclick="cycleMobileCarousel(this, -1, event)" style="pointer-events: auto; background: rgba(30, 35, 50, 0.7); color: white; border: 1px solid rgba(255,255,255,0.15); border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.3);"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg></button>
    <button class="mobile-next-btn" onclick="cycleMobileCarousel(this, 1, event)" style="pointer-events: auto; background: rgba(30, 35, 50, 0.7); color: white; border: 1px solid rgba(255,255,255,0.15); border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.3);"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg></button>
</div>
"""
    # Replace the first <div class="card-body-collapsible" ...>
    part2 = re.sub(r'(<div class="card-body-collapsible"([^>]*)>)', r'\1' + buttons, part2, count=1)
    text = analyst_split[0] + 'id="analyst-estimates-card">' + part2

# For Ownership Segment
owner_split = text.split('id="ownership-card">')
if len(owner_split) == 2:
    part2 = owner_split[1]
    part2 = re.sub(r'<div class="mobile-carousel-nav".*?</div>', '', part2, count=1, flags=re.DOTALL)
    
    buttons = """
<div class="mobile-carousel-nav-absolute" style="display: none; position: absolute; top: 55%; left: 0; width: 100%; justify-content: space-between; padding: 0 5px; z-index: 10; pointer-events: none;">
    <button class="mobile-prev-btn" onclick="cycleMobileCarousel(this, -1, event)" style="pointer-events: auto; background: rgba(30, 35, 50, 0.7); color: white; border: 1px solid rgba(255,255,255,0.15); border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.3);"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg></button>
    <button class="mobile-next-btn" onclick="cycleMobileCarousel(this, 1, event)" style="pointer-events: auto; background: rgba(30, 35, 50, 0.7); color: white; border: 1px solid rgba(255,255,255,0.15); border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.3);"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg></button>
</div>
"""
    part2 = re.sub(r'(<div class="card-body-collapsible"([^>]*)>)', r'\1' + buttons, part2, count=1)
    text = owner_split[0] + 'id="ownership-card">' + part2

with io.open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated arrows position successfully.")
