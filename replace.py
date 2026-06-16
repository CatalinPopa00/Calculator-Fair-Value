import re
with open('app.js', 'r') as f:
    content = f.read()


r1 = r"""                        <tr style="border-bottom:1px solid rgba\(255,255,255,0.04\);">
                            <td style="padding:4px 2px; color:var\(--text-main\); white-space:nowrap;">\$\{LABEL\[k\]\}</td>
                            <td style="text-align:right; padding:4px 2px; color:var\(--text-main\); white-space:nowrap;">\$\{\(bench \|\| 0\).toFixed\(1\)\}x</td>
                            <td style="text-align:right; padding:4px 2px; color:\$\{implColor\}; font-weight:600; white-space:nowrap;">\$\{safeImpl > 0 \? '\$' \+ fmt\(safeImpl\) : 'N/A'\}</td>
                            <td style="text-align:right; padding:4px 2px; color:var\(--accent\); font-weight:700; white-space:nowrap;" class="rel-weight-cell" data-key="\$\{k\}">\$\{\(w \* 100\).toFixed\(0\)\}%</td>
                        </tr>"""

r1n = r"""                        <tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
                            <td style="padding:8px 4px; color:var(--text-muted); font-weight:500; font-size:0.85rem; white-space:nowrap;">${LABEL[k]}</td>
                            <td style="text-align:right; padding:8px 4px; color:var(--text-main); font-family:var(--font-mono); font-weight:500; font-size:0.85rem; white-space:nowrap;">${(bench || 0).toFixed(1)}x</td>
                            <td style="text-align:right; padding:8px 4px; color:${safeImpl > 0 ? 'var(--text-main)' : 'var(--text-muted)'}; font-family:var(--font-mono); font-weight:600; font-size:0.85rem; white-space:nowrap;">${safeImpl > 0 ? '$' + fmt(safeImpl) : 'N/A'}</td>
                            <td style="text-align:right; padding:8px 4px; color:var(--accent); font-family:var(--font-mono); font-weight:700; font-size:0.85rem; white-space:nowrap;" class="rel-weight-cell" data-key="${k}">${(w * 100).toFixed(0)}%</td>
                        </tr>"""
content = re.sub(r1, r1n, content)

r2 = r"""                    <h4 style="font-size:0.8rem; color:var\(--text-muted\); text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;">Implied Values & Weights</h4>
                    <table style="width:100%; border-collapse:collapse; font-size:0.65rem; margin-bottom:1rem;">
                        <thead>
                            <tr style="border-bottom:1px solid rgba\(255,255,255,0.15\);">
                                <th style="text-align:left; padding:4px 2px; color:white; white-space:nowrap;">Metric</th>
                                <th style="text-align:right; padding:4px 2px; color:white; white-space:nowrap;">Benchmark</th>
                                <th style="text-align:right; padding:4px 2px; color:white; white-space:nowrap;">Implied FV</th>
                                <th style="text-align:right; padding:4px 2px; color:white; white-space:nowrap;">Weight</th>
                            </tr>
                        </thead>"""

r2n = r"""                    <h4 style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;">Implied Values & Weights</h4>
                    <table style="width:100%; border-collapse:collapse; margin-bottom:1rem;">
                        <thead>
                            <tr style="border-bottom:1px solid rgba(255,255,255,0.15);">
                                <th style="text-align:left; padding:8px 4px; color:var(--text-muted); font-size:0.8rem; font-weight:600; text-transform:uppercase; white-space:nowrap;">Metric</th>
                                <th style="text-align:right; padding:8px 4px; color:var(--text-muted); font-size:0.8rem; font-weight:600; text-transform:uppercase; white-space:nowrap;">Benchmark</th>
                                <th style="text-align:right; padding:8px 4px; color:var(--text-muted); font-size:0.8rem; font-weight:600; text-transform:uppercase; white-space:nowrap;">Implied FV</th>
                                <th style="text-align:right; padding:8px 4px; color:var(--text-muted); font-size:0.8rem; font-weight:600; text-transform:uppercase; white-space:nowrap;">Weight</th>
                            </tr>
                        </thead>"""
content = re.sub(r2, r2n, content)

with open('app.js', 'w') as f:
    f.write(content)
