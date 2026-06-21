        // --- ADDITIONAL SECTIONS ---
        const trendsBody = document.getElementById('trends-body');
        const anchors = data.historical_anchors;

        if (trendsBody) {
            if (anchors && anchors.length > 0) {
                // v44: Transposed Table with Sparklines
                const config = [
                    { label: 'Year', key: 'year', isHeader: true },
                    { label: 'Revenue (B)', key: 'revenue_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'revenue_b' },
                    { label: 'EPS', key: 'eps', formatter: v => (v != null) ? '$' + v.toFixed(2) : 'N/A', sparkKey: 'eps' },
                    { label: 'EPS (Adj.)', key: 'eps_adj', formatter: v => (v != null) ? '$' + v.toFixed(2) : 'N/A', sparkKey: 'eps_adj' },
                    { label: 'FCF (B)', key: 'fcf_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'fcf_b' },
                    { label: 'FCF Margin', key: 'fcf_margin_pct', formatter: v => (v != null) ? v : 'N/A', sparkKey: 'fcf_margin_pct' },
                    { label: 'Net Inc. (Adj, B)', key: 'net_income_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'net_income_b' },
                    { label: 'Net Margin (Adj)', key: 'net_margin_pct', formatter: v => (v != null) ? v : 'N/A', sparkKey: 'net_margin_pct' },
                    { label: 'Cash (B)', key: 'cash_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'cash_b' },
                    { label: 'Debt (B)', key: 'total_debt_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'total_debt_b' },
                    { label: 'Current Ratio', key: 'current_ratio', formatter: v => (v != null) ? v.toFixed(2) : 'N/A', sparkKey: 'current_ratio' },
                    { label: 'Shares (B)', key: 'shares_out_b', formatter: v => (v != null) ? v.toFixed(2) + ' B' : 'N/A', sparkKey: 'shares_out_b' },
                    { label: 'ROIC', key: 'roic_pct', formatter: v => (v != null) ? v : 'N/A', sparkKey: 'roic_pct' }
                ];

                const generateSparkline = (values) => {
                    if (!values || values.length < 2) return '';
                    const cleanValues = values.map(v => {
                        if (typeof v === 'string') return parseFloat(v.replace(/[^0-9.-]/g, '')) || 0;
                        return v || 0;
                    });
                    const min = Math.min(...cleanValues);
                    const max = Math.max(...cleanValues);
                    const range = (max - min) || 1;
                    const w = 40, h = 15;
                    const pts = cleanValues.map((v, i) => `${(i / (cleanValues.length - 1)) * w},${h - ((v - min) / range) * h}`).join(' ');
                    const color = cleanValues[cleanValues.length - 1] >= cleanValues[0] ? '#10b981' : '#ef4444';
                    return `<svg width="${w}" height="${h}" style="vertical-align:middle;margin-left:auto;"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>`;
                };

                let tableHtml = '';
                config.forEach(metric => {
                    const isYear = metric.key === 'year';
                    const sparkHtml = !isYear ? generateSparkline(anchors.map(a => a[metric.key]).reverse()) : '';

                    tableHtml += `<tr>`;
                    tableHtml += `
                        <td class="sticky-col" style="background: var(--card-bg); padding: 12px 16px; border-right: 1px solid rgba(255,255,255,0.05); min-width: 160px;">
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span style="font-weight: 700; color: var(--text-muted); text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px;">${metric.label}</span>
                                ${sparkHtml}
                            </div>
                        </td>`;

                    anchors.forEach(yearData => {
                        const val = yearData[metric.key];
                        let displayVal = metric.formatter ? metric.formatter(val) : val;
                        const cellStyle = isYear ? 'color: var(--primary); font-weight: 800; font-size: 0.95rem;' : 'color: white; font-weight: 600; font-size: 0.9rem;';
                        tableHtml += `<td style="padding: 12px 20px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.03); min-width: 90px; ${cellStyle}">${displayVal}</td>`;
                    });
                    tableHtml += `</tr>`;
                });

                trendsBody.innerHTML = tableHtml;
                document.getElementById('trends-scroll-wrapper').classList.add('transposed-view');
            } else {
                trendsBody.innerHTML = '<tr><td style="text-align: center; color: var(--text-muted); padding: 2rem;">No historical anchors available.</td></tr>';
            }
        }

        loadingState.style.display = 'none';
        watchlistView.style.display = 'none';
        dashboard.style.display = 'block';

        // Auto-load AI KPI Audit if we have previously loaded it
        if (typeof window.displayAiKpiAudit === 'function' && currentTicker) {
            try {
                let cachedList = JSON.parse(localStorage.getItem('kpiAuditCacheList') || '[]');
                if (cachedList.includes(currentTicker)) {
                    // It was loaded before, load it again silently (without forcing network)
                    window.displayAiKpiAudit(currentTicker, false);
                }
            } catch(e) {}
        }

        // Show deep research section (hidden by default to prevent empty state on page load)
        const deepResearch = document.getElementById('deep-research-section');
        if (deepResearch) deepResearch.style.display = '';

        renderHistoricalCharts(data);
        renderAnalystEstimatesInline(data.ticker);

