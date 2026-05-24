import os
import re

filepath = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value\app.js"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add updateBeneishUI
old_pio = '''    // ── Piotroski F-Score UI ──────────────────────────────────────────────────
    const updatePiotroskiUI = (scoreVal) => {'''

new_beneish = '''    // ── Beneish M-Score UI ────────────────────────────────────────────────────
    const updateBeneishUI = (beneishData) => {
        const circle = document.getElementById('beneish-score-circle');
        const fill   = document.getElementById('beneish-score-fill');
        const badge  = document.getElementById('beneish-label-badge');
        if (!circle || !fill) return;

        circle.className = 'score-circle';
        fill.className = 'score-bar-fill';
        circle.style.color = '';
        fill.style.backgroundColor = '';
        fill.style.width = '0%';

        if (!beneishData || beneishData.m_score == null) {
            circle.textContent = 'N/A';
            circle.style.color = 'var(--text-muted)';
            fill.style.backgroundColor = 'var(--text-muted)';
            if (badge) { badge.textContent = '--'; badge.style.background = 'rgba(148,163,184,0.2)'; badge.style.color = 'var(--text-muted)'; }
            return;
        }

        const scoreVal = beneishData.m_score;
        circle.textContent = scoreVal;
        
        // Bar logic for Beneish. Let's map -4.00 to 100% safe, and 0.00 to 0%
        let barPct = Math.round(((scoreVal - 0) / (-4.0 - 0)) * 100);
        if (barPct < 0) barPct = 0;
        if (barPct > 100) barPct = 100;
        
        setTimeout(() => { fill.style.width = `${barPct}%`; }, 50);

        if (beneishData.status === 'pass') {
            circle.classList.add('score-green');
            fill.classList.add('bg-score-green');
            if (badge) { badge.textContent = 'Safe'; badge.style.background = 'rgba(16,185,129,0.25)'; badge.style.color = 'var(--accent)'; }
        } else if (beneishData.status === 'fail') {
            circle.classList.add('score-red');
            fill.classList.add('bg-score-red');
            if (badge) { badge.textContent = 'Risk'; badge.style.background = 'rgba(239,68,68,0.2)'; badge.style.color = 'var(--danger)'; }
        } else {
            circle.style.color = 'var(--text-muted)';
            fill.style.backgroundColor = 'var(--text-muted)';
            if (badge) { badge.textContent = '--'; badge.style.background = 'rgba(148,163,184,0.2)'; badge.style.color = 'var(--text-muted)'; }
        }
    };

    // ── Piotroski F-Score UI ──────────────────────────────────────────────────
    const updatePiotroskiUI = (scoreVal) => {'''

content = content.replace(old_pio, new_beneish)


# 2. Add renderBeneishBreakdown
old_render_pio = '''    // ── Piotroski F-Score Breakdown Modal ──────────────────────
    function renderPiotroskiBreakdown(totalScore, breakdown) {'''

new_render_beneish = '''    // ── Beneish M-Score Breakdown Modal ──────────────────────
    function renderBeneishBreakdown(beneishData) {
        const modal = document.getElementById('score-modal');
        const body = document.getElementById('score-modal-body-content');
        const titleEl = document.getElementById('score-modal-title');
        if (!modal || !body) return;

        if (!beneishData || beneishData.m_score == null || !beneishData.breakdown || beneishData.breakdown.length === 0) {
            if (titleEl) titleEl.textContent = 'Beneish M-Score';
            body.innerHTML = '<p style="color:var(--text-muted);">No Beneish data available for this ticker.</p>';
            modal.style.display = 'flex';
            return;
        }

        const scoreVal = beneishData.m_score;
        let html = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding-bottom:5px; gap:15px;">
                <h3 style="margin:0; font-size:1.05rem; color:white; font-weight:800;">Beneish M-Score</h3>
                <div style="display:flex; align-items:baseline; gap:6px;">
                    <span style="font-size:0.75rem; color:var(--text-muted); font-weight:600; text-transform:uppercase;">Total:</span>
                    <span style="font-size:1.3rem; font-weight:900; color:white;">${scoreVal}</span>
                </div>
            </div>
            <div style="margin-bottom: 15px; font-size: 0.85rem; color: var(--text-muted);">
                A score less than <b>-1.78</b> suggests a low risk of accounting manipulation. Higher scores indicate increased risk.
            </div>
        `;

        beneishData.breakdown.forEach(item => {
            const label = item.metric || 'Unknown';
            const passed = item.status === 'pass';
            const dotColor = passed ? 'var(--accent)' : (item.status === 'fail' ? 'var(--danger)' : 'var(--text-muted)');

            html += `
                <div style="display:grid; grid-template-columns: 1fr auto auto; align-items:center; padding:8px 0; border-top:1px solid rgba(255,255,255,0.04); gap:15px;">
                    <div>
                        <div style="font-weight:600; font-size:0.85rem; color:white; overflow:hidden; text-overflow:ellipsis;">${label}</div>
                        <div style="font-size:0.7rem; color:var(--text-muted); margin-top:2px;">${item.threshold}</div>
                    </div>
                    <div style="font-weight:700; font-size:0.85rem; color:rgba(255,255,255,0.7); text-align:right; font-family:monospace; min-width:60px;">${item.value !== null ? item.value : 'N/A'}</div>
                    <div style="display:flex; align-items:center; gap:8px; justify-content:flex-end; min-width:20px;">
                        <span style="width:8px; height:8px; border-radius:50%; background:${dotColor}; display:inline-block; flex-shrink:0;"></span>
                    </div>
                </div>
            `;
        });

        if (titleEl) titleEl.textContent = '';
        body.innerHTML = html;
        modal.style.display = 'flex';
    }

    // ── Piotroski F-Score Breakdown Modal ──────────────────────
    function renderPiotroskiBreakdown(totalScore, breakdown) {'''

content = content.replace(old_render_pio, new_render_beneish)


# 3. Replace updateUI logic
old_ui_logic = '''        // Beneish M-Score UI Update
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
        }'''

new_ui_logic = '''        // Beneish M-Score UI Update
        const beneishData = data.health_score ? data.health_score.beneish : null;
        updateBeneishUI(beneishData);
        
        const bRow = document.getElementById('beneish-score-row');
        if (bRow) {
            bRow.style.cursor = 'pointer';
            bRow.onclick = () => {
                renderBeneishBreakdown(beneishData);
            };
        }'''

content = content.replace(old_ui_logic, new_ui_logic)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated app.js Beneish logic")
