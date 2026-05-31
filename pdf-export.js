document.addEventListener('DOMContentLoaded', () => {
    const exportBtn = document.getElementById('export-pdf-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            if (!window.globalData || !window.globalData.ticker) {
                alert('Please search for a company first.');
                return;
            }

            const btnOriginalHtml = exportBtn.innerHTML;
            exportBtn.innerHTML = '<div class="spinner" style="width: 20px; height: 20px; border-width: 2px;"></div> Exporting...';
            exportBtn.disabled = true;

            try {
                const container = document.getElementById('pdf-export-container');
                container.innerHTML = ''; // clear

                // Get Data
                const d = window.globalData;
                const p = d.company_profile || {};
                const q = d.quote || {};

                const price = q.price ? q.price.toFixed(2) : 'N/A';
                const mktCapRaw = p.mktCap || q.marketCap;
                const mktCap = mktCapRaw ? (mktCapRaw / 1e9).toFixed(2) + 'B' : 'N/A';
                const ind = p.industry || 'N/A';
                const name = p.companyName || d.ticker;
                const ticker = d.ticker;

                // Scenario values
                const baseVal = document.getElementById('fair-value-display')?.innerText || 'N/A';
                const bearVal = document.getElementById('bear-value-display')?.innerText || 'N/A';
                const bullVal = document.getElementById('bull-value-display')?.innerText || 'N/A';

                // Weights
                const wDcf = document.getElementById('dcf-weight')?.value || '25';
                const wRel = document.getElementById('rel-weight')?.value || '10';
                const wFwd = document.getElementById('fwd-weight')?.value || '40';
                const wPeg = document.getElementById('peg-weight')?.value || '25';

                // Build wrapper inside container to handle padding
                const wrapper = document.createElement('div');
                wrapper.style.padding = '40px';
                wrapper.style.background = '#0b1320'; // Match site dark mode
                wrapper.style.color = '#f8fafc';
                wrapper.style.fontFamily = "'Outfit', sans-serif";
                container.appendChild(wrapper);

                // Build Row 1
                const row1 = document.createElement('div');
                row1.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 30px; background: rgba(30, 41, 59, 1); border-radius: 16px; margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 10px 30px rgba(0,0,0,0.5);';
                row1.innerHTML = `
                    <div>
                        <h2 style="margin: 0 0 15px 0; font-size: 2.5rem; font-weight: 800;">${name} <span style="color: #94a3b8; font-weight: 400;">${ticker}</span></h2>
                        <div style="font-size: 1.1rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;">CURRENT PRICE</div>
                        <div style="font-size: 3rem; font-weight: 800;">$${price}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.1rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;">INDUSTRY</div>
                        <div style="font-size: 1.4rem; font-weight: 600; margin-bottom: 25px;">${ind}</div>
                        <div style="font-size: 1.1rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;">MARKET CAP</div>
                        <div style="font-size: 1.4rem; font-weight: 600;">$${mktCap}</div>
                    </div>
                `;
                wrapper.appendChild(row1);

                // Build Row 2
                const row2 = document.createElement('div');
                row2.style.cssText = 'display: flex; gap: 20px; margin-bottom: 35px; align-items: stretch;';
                row2.innerHTML = `
                    <div style="flex: 1; text-align: center; padding: 30px; background: rgba(30, 41, 59, 1); border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column; justify-content: center;">
                        <h3 style="margin: 0 0 15px 0; color: #94a3b8; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 1px;">Bear Scenario</h3>
                        <div style="font-size: 2.2rem; font-weight: 800;">${bearVal}</div>
                    </div>
                    <div style="flex: 1; text-align: center; padding: 30px; background: rgba(30, 41, 59, 1); border-radius: 16px; border: 2px solid #3b82f6; box-shadow: 0 0 30px rgba(59, 130, 246, 0.15); display: flex; flex-direction: column; justify-content: center;">
                        <h3 style="margin: 0 0 15px 0; color: #3b82f6; font-size: 1.3rem; text-transform: uppercase; letter-spacing: 1px;">Base Scenario</h3>
                        <div style="font-size: 2.8rem; font-weight: 800; color: #3b82f6;">${baseVal}</div>
                    </div>
                    <div style="flex: 1; text-align: center; padding: 30px; background: rgba(30, 41, 59, 1); border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column; justify-content: center;">
                        <h3 style="margin: 0 0 15px 0; color: #94a3b8; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 1px;">Bull Scenario</h3>
                        <div style="font-size: 2.2rem; font-weight: 800;">${bullVal}</div>
                    </div>
                    <div style="flex: 1.2; padding: 30px; background: rgba(30, 41, 59, 1); border-radius: 16px; border: 1px solid rgba(255,255,255,0.1);">
                        <h3 style="margin: 0 0 25px 0; font-size: 1.3rem; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 15px;">Model Weights (%)</h3>
                        <div style="display: grid; grid-template-columns: 1fr auto; gap: 18px; font-size: 1.15rem; color: #94a3b8; align-items: center;">
                            <div>DCF Model</div><div style="font-weight:bold; color: #f8fafc; background: rgba(0,0,0,0.3); padding: 4px 12px; border-radius: 6px;">${wDcf}</div>
                            <div>Relative Valuation</div><div style="font-weight:bold; color: #f8fafc; background: rgba(0,0,0,0.3); padding: 4px 12px; border-radius: 6px;">${wRel}</div>
                            <div>Forward Multiple</div><div style="font-weight:bold; color: #f8fafc; background: rgba(0,0,0,0.3); padding: 4px 12px; border-radius: 6px;">${wFwd}</div>
                            <div>PEG Valuation</div><div style="font-weight:bold; color: #f8fafc; background: rgba(0,0,0,0.3); padding: 4px 12px; border-radius: 6px;">${wPeg}</div>
                        </div>
                    </div>
                `;
                wrapper.appendChild(row2);

                // Clone Rows 3, 4, 5
                const cloneAndAppend = (selector) => {
                    const el = document.querySelector(selector);
                    if (el) {
                        const clone = el.cloneNode(true);
                        
                        // Copy canvas data since cloneNode doesn't copy pixel data
                        const sourceCanvases = el.querySelectorAll('canvas');
                        const clonedCanvases = clone.querySelectorAll('canvas');
                        sourceCanvases.forEach((canvas, i) => {
                            clonedCanvases[i].getContext('2d').drawImage(canvas, 0, 0);
                        });
                        
                        // Force clone to stay in layout and not overflow or shrink weirdly
                        clone.style.margin = '0 0 30px 0';
                        clone.style.width = '100%';
                        
                        wrapper.appendChild(clone);
                    }
                };

                cloneAndAppend('.row-2-card'); // Row 3
                cloneAndAppend('#methods-container'); // Row 4
                cloneAndAppend('#analyst-estimates-card'); // Row 5

                // Small delay to allow browser to render the hidden elements before snapshotting
                await new Promise(resolve => setTimeout(resolve, 500));

                // Generate PDF
                const opt = {
                    margin:       0,
                    filename:     `${ticker}_Fair_Value_Report.pdf`,
                    image:        { type: 'jpeg', quality: 0.98 },
                    html2canvas:  { 
                        scale: 2, 
                        useCORS: true, 
                        logging: false, 
                        windowWidth: 1200, // Forces the wide layout to trigger
                        backgroundColor: '#0b1320'
                    },
                    jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
                };
                
                // Using Letter portrait is fine, html2pdf will scale it down to fit width by default
                await html2pdf().set(opt).from(container).save();

            } catch(e) {
                console.error("PDF Export Error:", e);
                alert('Error generating PDF. Check console for details.');
            } finally {
                // Cleanup
                const container = document.getElementById('pdf-export-container');
                container.innerHTML = '';
                exportBtn.innerHTML = btnOriginalHtml;
                exportBtn.disabled = false;
            }
        });
    }
});
