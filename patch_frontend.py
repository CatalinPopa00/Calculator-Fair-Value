import sys
import re

try:
    with open('style.css', 'r', encoding='utf-8') as f:
        css = f.read()

    new_css = """
/* Historical Anchors Toggle */
.anchors-toggle-wrapper {
    display: flex;
    background: rgba(var(--invert-rgb), 0.05);
    border-radius: 6px;
    padding: 2px;
    width: fit-content;
}
.anchors-toggle-btn {
    padding: 4px 10px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--text-muted);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s ease;
    border: none;
    background: transparent;
}
.anchors-toggle-btn.active {
    background: var(--primary);
    color: var(--text-main);
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}
"""
    if ".anchors-toggle-wrapper" not in css:
        css += "\n" + new_css
        with open('style.css', 'w', encoding='utf-8') as f:
            f.write(css)
        print("style.css patched")
except Exception as e:
    print("Error css:", e)

try:
    with open('app.js', 'r', encoding='utf-8') as f:
        app = f.read()

    target_block = """        // --- ADDITIONAL SECTIONS ---
        const trendsBody = document.getElementById('trends-body');
        const anchors = data.historical_anchors;

        if (trendsBody) {
            if (anchors && anchors.length > 0) {"""
            
    replacement_block = """        // --- ADDITIONAL SECTIONS ---
        window._currentAnchorData = data;
        if (!window._currentAnchorView) window._currentAnchorView = 'year';

        window.renderAnchorsTable = function(viewType) {
            if (viewType) window._currentAnchorView = viewType;
            const trendsBody = document.getElementById('trends-body');
            const anchors = window._currentAnchorView === 'quarter' ? window._currentAnchorData.quarterly_anchors : window._currentAnchorData.historical_anchors;

            if (trendsBody) {
                if (anchors && anchors.length > 0) {"""

    app = app.replace(target_block, replacement_block)
    
    target_inner = """                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span style="font-weight: 700; color: var(--text-muted); text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px;">${metric.label}</span>
                                ${sparkHtml}
                            </div>"""
                            
    replacement_inner = """                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                ${isYear ? `
                                <div class="anchors-toggle-wrapper">
                                    <button class="anchors-toggle-btn ${window._currentAnchorView === 'year' ? 'active' : ''}" onclick="window.renderAnchorsTable('year')">Year</button>
                                    <button class="anchors-toggle-btn ${window._currentAnchorView === 'quarter' ? 'active' : ''}" onclick="window.renderAnchorsTable('quarter')">Quarter</button>
                                </div>
                                ` : `<span style="font-weight: 700; color: var(--text-muted); text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px;">${metric.label}</span>`}
                                ${sparkHtml}
                            </div>"""
    
    app = app.replace(target_inner, replacement_inner)
    
    # After trendsBody.innerHTML = tableHtml, we need to close the render function correctly.
    target_close = """                trendsBody.innerHTML = tableHtml;
                document.getElementById('trends-scroll-wrapper').classList.add('transposed-view');
            } else {
                trendsBody.innerHTML = '<tr><td style="text-align: center; color: var(--text-muted); padding: 2rem;">No historical anchors available.</td></tr>';
            }
        }"""
        
    replacement_close = """                trendsBody.innerHTML = tableHtml;
                document.getElementById('trends-scroll-wrapper').classList.add('transposed-view');
            } else {
                trendsBody.innerHTML = '<tr><td style="text-align: center; color: var(--text-muted); padding: 2rem;">No historical anchors available.</td></tr>';
            }
        }
        }; // end of window.renderAnchorsTable
        
        window.renderAnchorsTable(); // Initial call"""
        
    if "}; // end of window.renderAnchorsTable" not in app:
        app = app.replace(target_close, replacement_close)
        
        with open('app.js', 'w', encoding='utf-8') as f:
            f.write(app)
        print("app.js patched")
    else:
        print("app.js already patched")

except Exception as e:
    print("Error app:", e)
