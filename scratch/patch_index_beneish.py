import os

filepath = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the old Beneish block with the new styled one
old_html = '''                            <!-- Beneish M-Score -->
                            <div class="score-row" id="beneish-score-row" style="margin-top: 1rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 1rem;">
                                <span class="label" style="display: block; margin-bottom: 0.3rem; font-weight: 500; font-size: 0.85rem;">
                                    Beneish M-Score <span style="font-size:0.7rem; color:var(--text-muted);">(Manipulation Risk)</span>
                                </span>
                                <div class="score-display" style="display: flex; flex-direction: column; align-items: flex-start; justify-content: center; width: 100%;">
                                    <div id="beneish-score-value" style="font-weight: 600; font-size: 1rem;">N/A</div>
                                    <div id="beneish-score-label" style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem;"></div>
                                </div>
                            </div>'''

new_html = '''                            <!-- Beneish M-Score -->
                            <div class="score-row" id="beneish-score-row" style="cursor: pointer; margin-top: 1rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 1rem;"
                                title="Click to see Beneish M-Score details">
                                <span class="label" style="display: block; margin-bottom: 0.3rem; font-weight: 500; font-size: 0.85rem;">
                                    Beneish M-Score <span style="font-size:0.7rem; color:var(--text-muted);">(Manipulation Risk)</span>
                                    <span id="beneish-label-badge" style="display: inline-block; margin-left: 8px; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; background: rgba(148,163,184,0.2); color: var(--text-muted);">--</span>
                                </span>
                                <div class="score-display">
                                    <div class="score-circle" id="beneish-score-circle" style="font-size:0.8rem; width:45px; height:45px;">N/A</div>
                                    <div class="score-bar-wrapper">
                                        <div class="score-bar-fill" id="beneish-score-fill"></div>
                                    </div>
                                    <div class="score-max" style="margin-left: 10px; color: var(--text-muted); font-size: 0.8rem;">
                                        < -1.78
                                    </div>
                                </div>
                            </div>'''

content = content.replace(old_html, new_html)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated index.html Beneish UI")
