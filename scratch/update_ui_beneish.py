import os
import re

# 1. Update index.html
html_filepath = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value\index.html"
with open(html_filepath, 'r', encoding='utf-8') as f:
    content = f.read()

beneish_html = '''
                            <!-- Beneish M-Score -->
                            <div class="score-row" id="beneish-score-row" style="margin-top: 1rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 1rem;">
                                <span class="label" style="display: block; margin-bottom: 0.3rem; font-weight: 500; font-size: 0.85rem;">
                                    Beneish M-Score <span style="font-size:0.7rem; color:var(--text-muted);">(Manipulation Risk)</span>
                                </span>
                                <div class="score-display" style="display: flex; flex-direction: column; align-items: flex-start; justify-content: center; width: 100%;">
                                    <div id="beneish-score-value" style="font-weight: 600; font-size: 1rem;">N/A</div>
                                    <div id="beneish-score-label" style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem;"></div>
                                </div>
                            </div>
'''

if 'id="beneish-score-row"' not in content:
    target = "<!-- Right 50%: Algorithmic Insights -->"
    # insert before target, but inside the left column
    content = content.replace('                        </div>\n\n                        <!-- Right 50%: Algorithmic Insights -->', beneish_html + '                        </div>\n\n                        <!-- Right 50%: Algorithmic Insights -->')
    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated index.html")


# 2. Update app.js and variants
js_files = ['app.js', 'vercel_app.js', 'vercel_app_v234.js']
js_snippet = '''
        // Beneish M-Score UI Update
        const bRow = document.getElementById('beneish-score-row');
        const bVal = document.getElementById('beneish-score-value');
        const bLab = document.getElementById('beneish-score-label');
        if (bRow && bVal && bLab && data.health_score && data.health_score.beneish) {
            const bData = data.health_score.beneish;
            if (bData.m_score !== null) {
                bVal.textContent = bData.m_score;
                bLab.textContent = bData.label;
                if (bData.status === 'pass') {
                    bVal.style.color = 'var(--success)';
                    bLab.style.color = 'var(--success)';
                } else if (bData.status === 'fail') {
                    bVal.style.color = 'var(--danger)';
                    bLab.style.color = 'var(--danger)';
                } else {
                    bVal.style.color = 'var(--text-muted)';
                    bLab.style.color = 'var(--text-muted)';
                }
            } else {
                bVal.textContent = 'N/A';
                bVal.style.color = 'var(--text-muted)';
                bLab.textContent = bData.label || 'Data Unavailable';
                bLab.style.color = 'var(--text-muted)';
            }
        }
'''

for filename in js_files:
    filepath = os.path.join(r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value", filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        js_content = f.read()
        
    if '// Beneish M-Score UI Update' not in js_content:
        target = "// Rule of 40 UI Update & Click Binding"
        js_content = js_content.replace(target, js_snippet + "\n        " + target)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(js_content)
        print(f"Updated {filename}")
