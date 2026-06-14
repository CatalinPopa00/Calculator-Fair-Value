import io

with io.open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target1 = '<button class="mobile-prev-btn" onclick="cycleMobileCarousel(this, -1, event)" style="background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; cursor: pointer;">&larr;</button>'
replace1 = '<button class="mobile-prev-btn" onclick="cycleMobileCarousel(this, -1, event)" style="background: rgba(30, 35, 50, 0.7); color: white; border: 1px solid rgba(255,255,255,0.15); border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.3);"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg></button>'

target2 = '<button class="mobile-next-btn" onclick="cycleMobileCarousel(this, 1, event)" style="background: var(--accent); color: #000; border: none; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-weight: bold;">&rarr;</button>'
replace2 = '<button class="mobile-next-btn" onclick="cycleMobileCarousel(this, 1, event)" style="background: rgba(30, 35, 50, 0.7); color: white; border: 1px solid rgba(255,255,255,0.15); border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.3);"><svg width="18" height=\"18\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><polyline points=\"9 18 15 12 9 6\"></polyline></svg></button>'

text = text.replace(target1, replace1)
text = text.replace(target2, replace2)

with io.open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Replaced successfully")
