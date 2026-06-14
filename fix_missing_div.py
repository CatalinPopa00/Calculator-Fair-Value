import io

with io.open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                                        </div>
    
    <svg class="chevron-icon collapsible-trigger" data-card="historical-anchors"'''

replace = '''                                        </div>
    </div>
    <svg class="chevron-icon collapsible-trigger" data-card="historical-anchors"'''

text = text.replace(target, replace)

with io.open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed missing div")
