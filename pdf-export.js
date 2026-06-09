document.addEventListener('DOMContentLoaded', () => {
    const exportBtn = document.getElementById('export-pdf-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            if (typeof html2canvas === 'undefined' || typeof window.jspdf === 'undefined') {
                alert('PDF libraries not fully loaded yet. Please try again in a moment.');
                return;
            }

            const jsPDF = window.jspdf.jsPDF;
            console.log("PDF export process started...");

            // Save state
            const btnOriginalHtml = exportBtn.innerHTML;
            exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> GENERATING...';
            exportBtn.disabled = true;

            const originalScrollY = window.scrollY;

            try {
                // Fetch data
                const d = window.globalData || {};
                const p = d.company_profile || {};
                const q = d.quote || {};

                const price = q.price ? q.price.toFixed(2) : 'N/A';
                const mktCapRaw = p.mktCap || q.marketCap;
                const mktCap = mktCapRaw ? (mktCapRaw / 1e9).toFixed(2) + 'B' : 'N/A';
                const ind = p.industry || 'N/A';
                const name = p.companyName || d.ticker || 'Company';
                const ticker = d.ticker || 'N/A';

                const baseVal = document.getElementById('fair-value-display')?.innerText || 'N/A';
                const bearVal = document.getElementById('bear-value-display')?.innerText || 'N/A';
                const bullVal = document.getElementById('bull-value-display')?.innerText || 'N/A';

                const wDcf = document.getElementById('dcf-weight')?.value || '25';
                const wRel = document.getElementById('rel-weight')?.value || '10';
                const wFwd = document.getElementById('fwd-weight')?.value || '40';
                const wPeg = document.getElementById('peg-weight')?.value || '25';

                // 1. Build the clone container
                const container = document.createElement('div');
                container.id = 'pdf-export-temp-container';
                container.style.width = '1200px';
                container.style.background = '#0b1320';
                container.style.color = '#f8fafc';
                container.style.fontFamily = "'Outfit', sans-serif";
                container.style.padding = '40px';
                container.style.position = 'absolute';
                container.style.top = '0';
                container.style.left = '0';
                container.style.zIndex = '-9999'; // hide behind actual UI
                // Prevent inherited flexbox weirdness
                container.style.display = 'block';

                // Row 1
                container.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 30px; background: rgba(30, 41, 59, 1); border-radius: 16px; margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.1);">
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
                    </div>

                    <div style="display: flex; gap: 20px; margin-bottom: 35px; align-items: stretch;">
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
                    </div>
                `;

                // Add to body so clones work properly
                document.body.appendChild(container);

                const appendCloned = (selector) => {
                    const el = document.querySelector(selector);
                    if (el) {
                        const clone = el.cloneNode(true);
                        clone.style.margin = '0 0 30px 0';
                        clone.style.width = '100%';
                        clone.style.maxWidth = '100%';
                        clone.style.display = 'block';

                        // Convert canvases to images
                        const originalCanvases = el.querySelectorAll('canvas');
                        const clonedCanvases = clone.querySelectorAll('canvas');
                        
                        originalCanvases.forEach((orig, idx) => {
                            try {
                                const dataUrl = orig.toDataURL('image/png');
                                const img = document.createElement('img');
                                img.src = dataUrl;
                                img.style.width = orig.style.width || orig.width + 'px';
                                img.style.height = orig.style.height || orig.height + 'px';
                                clonedCanvases[idx].parentNode.replaceChild(img, clonedCanvases[idx]);
                            } catch(e) {}
                        });
                        container.appendChild(clone);
                    }
                };

                appendCloned('.row-2-card');
                appendCloned('#methods-container');
                appendCloned('#analyst-estimates-card');

                // Force layout calculation
                window.scrollTo(0, 0);
                await new Promise(r => setTimeout(r, 500));

                // 2. Generate Canvas manually via html2canvas
                const canvas = await html2canvas(container, {
                    scale: 2, // High resolution
                    useCORS: true,
                    logging: false,
                    scrollY: 0,
                    scrollX: 0,
                    width: 1200,
                    windowWidth: 1200,
                    backgroundColor: '#0b1320'
                });

                // 3. Generate PDF manually via jsPDF
                const imgData = canvas.toDataURL('image/jpeg', 0.95);
                const pdf = new jsPDF('p', 'mm', 'a4');
                
                // A4 dimensions (210x297mm)
                const pdfWidth = 210;
                const pdfHeight = 297;

                // Calculate ratio to fit A4 width
                const imgProps = pdf.getImageProperties(imgData);
                const ratio = imgProps.width / pdfWidth;
                const imgHeightInMm = imgProps.height / ratio;

                let heightLeft = imgHeightInMm;
                let position = 0;

                // Add first page
                pdf.addImage(imgData, 'JPEG', 0, position, pdfWidth, imgHeightInMm);
                heightLeft -= pdfHeight;

                // Add subsequent pages if content overflows A4 height
                while (heightLeft > 0) {
                    position -= pdfHeight;
                    pdf.addPage();
                    pdf.addImage(imgData, 'JPEG', 0, position, pdfWidth, imgHeightInMm);
                    heightLeft -= pdfHeight;
                }

                // Download
                console.log("Saving PDF...");
                pdf.save(`${ticker}_Fair_Value_Report.pdf`);
                console.log("PDF saved!");

            } catch (e) {
                console.error("PDF Export Error:", e);
                alert("Failed to export PDF.");
            } finally {
                const c = document.getElementById('pdf-export-temp-container');
                if (c) c.remove();

                window.scrollTo(0, originalScrollY);
                exportBtn.innerHTML = btnOriginalHtml;
                exportBtn.disabled = false;
            }
        });
    }
});
