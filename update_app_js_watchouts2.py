import io
import re

with io.open('app.js', 'r', encoding='utf-8') as f:
    text = f.read()

target = "} else if (activeTab === 'news') {"
replace = """} else if (activeTab === 'watchouts') {
                        if (isLoadingAI) {
                            panel.innerHTML = `
                                <div style="display: flex; flex-direction: column; gap: 10px; width: 100%;">
                                    <h4 style="color: #fbbf24; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 5px; font-weight: 800;">Earnings Watchouts</h4>
                                    <div class="skeleton-text" style="width: 100%; height: 25px; border-radius: 6px;"></div>
                                    <div class="skeleton-text" style="width: 100%; height: 25px; border-radius: 6px;"></div>
                                    <div class="skeleton-text" style="width: 90%; height: 25px; border-radius: 6px;"></div>
                                </div>
                            `;
                        } else {
                            const watchoutsHtml = parsed.earningsWatchouts && parsed.earningsWatchouts.length > 0
                                ? parsed.earningsWatchouts.map(w => `
                                    <div style="display: flex; gap: 10px; margin-bottom: 8px; align-items: flex-start; background: rgba(251, 191, 36, 0.04); border: 1px solid rgba(251, 191, 36, 0.1); padding: 8px 12px; border-radius: 6px;">
                                        <span style="color: #fbbf24; font-weight: bold; font-size: 0.9rem; flex-shrink:0;">📌</span>
                                        <span style="color: rgba(255,255,255,0.85); font-size: 0.8rem;">${w}</span>
                                    </div>`).join('')
                                : '<div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; padding: 10px; font-style:italic;">No specific earnings watchouts identified.</div>';

                            panel.innerHTML = `
                                <div style="display: flex; flex-direction: column; width: 100%;">
                                    <h4 style="color: #fbbf24; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; margin-bottom: 10px; font-weight: 800;">Key Points from Latest Reports</h4>
                                    ${watchoutsHtml}
                                </div>
                            `;
                        }
                    } else if (activeTab === 'news') {"""

if "else if (activeTab === 'watchouts')" not in text:
    text = text.replace(target, replace)
    with io.open('app.js', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Updated app.js for watchouts rendering")
else:
    print("Already updated")
