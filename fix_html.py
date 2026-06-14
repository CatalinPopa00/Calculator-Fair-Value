import io

with io.open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '<div class="hist-toggle-wrapper" style="width: 100%; display: flex; justify-content: center; margin-top: 15px; margin-bottom: 5px;" onclick="event.stopPropagation();">'
replace = '<div class="hist-toggle-wrapper" style="display: flex; justify-content: center;" onclick="event.stopPropagation();">'
text = text.replace(target, replace)

# 2. Historical Stability Title
target2 = '<h3 id="historical-title" class="research-title collapsible-trigger" data-card="historical-charts" style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin: 0; width: 100%;">'
replace2 = '<h3 id="historical-title" class="research-title collapsible-trigger" data-card="historical-charts" style="display: flex; align-items: center; justify-content: flex-start; gap: 10px; cursor: pointer; margin: 0; width: 100%;">'
text = text.replace(target2, replace2)

with io.open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed HTML elements")
