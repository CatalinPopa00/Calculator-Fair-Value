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

            const originalScrollY = window.scrollY;
            window.scrollTo(0, 0); // Reset scroll to avoid html2canvas clipping bugs

            try {
                // The container MUST be in the DOM to have its layout/height calculated properly.
                const container = document.createElement('div');
                container.style.width = '1200px';
                container.style.background = '#0b1320';
                container.style.color = '#f8fafc';
                container.style.fontFamily = "'Outfit', sans-serif";
                container.style.padding = '40px';
                
                // Position absolute and off-screen left so layout calculates at exactly 1200px width.
                container.id = 'pdf-export-temp-container';
                container.style.position = 'absolute';
                container.style.left = '-15000px';
                container.style.top = '0';
                container.style.width = '1200px';
                
                document.body.appendChild(container);

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

                // Build Row 1
                const row1 = document.createElement('div');
                row1.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 30px; background: rgba(30, 41, 59, 1); border-radius: 16px; margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.1);';
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
                container.appendChild(row1);

                // Build Row 2
                const row2 = document.createElement('div');
                row2.style.cssText = 'display: flex; gap: 20px; margin-bottom: 35px; align-items: stretch;';
                row2.innerHTML = `
                    <div style="flex: 1; text-align: center; padding: 30px; background: rgba(30, 41, 59, 1); border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column; justify-content: center;">
                        <h3 style="margin: 0 0 15px 0; color: #94a3b8; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 1px;">Bear Scenario</h3>
                        <div style="font-size: 2.2rem; font-weight: 800;">${bearVal}</div>
                    </div>
                    <div style="flex: 1; text-align: center; padding: 30px; background: rgba(30, 41, 59, 1); border-radius: 16px; border: 2px solid #3b82f6; display: flex; flex-direction: column; justify-content: center;">
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
                container.appendChild(row2);

                // Clone Rows 3, 4, 5
                const cloneAndAppend = (selector) => {
                    const el = document.querySelector(selector);
                    if (el) {
                        const clone = el.cloneNode(true);
                        
                        // Overwrite potential weird classes or widths inherited from body flex
                        clone.style.width = '100%';
                        clone.style.maxWidth = '100%';

                        // Replace canvases with images to avoid html2canvas blank canvas bug
                        const sourceCanvases = el.querySelectorAll('canvas');
                        const clonedCanvases = clone.querySelectorAll('canvas');
                        sourceCanvases.forEach((canvas, i) => {
                            const img = document.createElement('img');
                            img.src = canvas.toDataURL('image/png');
                            img.style.width = canvas.style.width || canvas.width + 'px';
                            img.style.height = canvas.style.height || canvas.height + 'px';
                            clonedCanvases[i].parentNode.replaceChild(img, clonedCanvases[i]);
                        });
                        
                        // Force clone to stay in layout
                        clone.style.margin = '0 0 30px 0';
                        clone.style.width = '100%';
                        
                        container.appendChild(clone);
                    }
                };

                cloneAndAppend('.row-2-card'); // Row 3
                cloneAndAppend('#methods-container'); // Row 4
                cloneAndAppend('#analyst-estimates-card'); // Row 5

                // Small delay to allow browser to calculate layout fully
                await new Promise(resolve => setTimeout(resolve, 800));

                // Generate PDF
                const opt = {
                    margin:       0,
                    filename:     `${ticker}_Fair_Value_Report.pdf`,
                    image:        { type: 'jpeg', quality: 0.98 },
                    html2canvas:  { 
                        scale: 2,
                        scrollX: 0,
                        scrollY: 0,
                        useCORS: true, 
                        logging: false, 
                        windowWidth: 1200,
                        backgroundColor: '#0b1320',
                        onclone: (clonedDoc) => {
                            // Reset the container position so html2canvas measures it properly
                            const clonedContainer = clonedDoc.getElementById('pdf-export-temp-container');
                            if (clonedContainer) {
                                clonedContainer.style.position = 'static';
                                clonedContainer.style.left = '0';
                            }
                            clonedDoc.body.style.overflow = 'visible';

                            const allElements = clonedDoc.querySelectorAll('*');
                            allElements.forEach(el => {
                                el.style.backdropFilter = 'none';
                                el.style.webkitBackdropFilter = 'none';
                                if (el.classList && el.classList.contains('glass-card')) {
                                    el.style.backgroundColor = '#1e293b'; 
                                }
                            });
                        }
                    },
                    pagebreak:    { mode: ['css', 'legacy'] },
                    jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
                };
                
                await html2pdf().set(opt).from(container).save();

                // Cleanup
                if (document.body.contains(container)) {
                    document.body.removeChild(container);
                }

            } catch(e) {
                console.error("PDF Export Error:", e);
                alert('Error generating PDF. Check console for details.');
            } finally {
                window.scrollTo(0, originalScrollY);
                exportBtn.innerHTML = btnOriginalHtml;
                exportBtn.disabled = false;
            }
        });
    }
});
