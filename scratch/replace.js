const fs = require('fs');

let content = fs.readFileSync('pdf-export.js', 'utf8');

// Replace the container creation logic
const containerStart = content.indexOf("const container = document.createElement('div');");
const containerEnd = content.indexOf('                const appendCloned = (selector, targetContainerId) => {');

const newContainerHTML = `
                // --- PAGE 1 CONTAINER ---
                const container1 = document.createElement('div');
                container1.id = 'pdf-export-temp-container-1';
                container1.style.position = 'absolute';
                container1.style.left = '-9999px';
                container1.style.top = '0';
                container1.style.width = '1200px';
                container1.style.background = '#0f172a';
                container1.style.color = '#f8fafc';
                container1.style.fontFamily = "'Inter', sans-serif";
                container1.style.padding = '40px';
                container1.style.boxSizing = 'border-box';
                container1.style.zIndex = '-1';
                document.body.appendChild(container1);

                // --- PAGE 2 CONTAINER ---
                const container2 = document.createElement('div');
                container2.id = 'pdf-export-temp-container-2';
                container2.style.position = 'absolute';
                container2.style.left = '-9999px';
                container2.style.top = '0';
                container2.style.width = '1200px';
                container2.style.background = '#0f172a';
                container2.style.color = '#f8fafc';
                container2.style.fontFamily = "'Inter', sans-serif";
                container2.style.padding = '40px';
                container2.style.boxSizing = 'border-box';
                container2.style.zIndex = '-1';
                document.body.appendChild(container2);

                const cardStyle = "background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px;";

                container1.innerHTML = \`
                    <!-- Top Header Info -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <div style="display: flex; align-items: center; gap: 40px;">
                            <div style="display: flex; align-items: center; gap: 15px;">
                                \${logoHtml}
                                <div style="display: flex; flex-direction: column; line-height: 1.1;">
                                    <h2 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #f8fafc;">\${ticker}</h2>
                                    <span style="color: #94a3b8; font-weight: 500; font-size: 1.1rem; margin-top: 4px;">\${name}</span>
                                </div>
                            </div>
                            <div style="display: flex; flex-direction: column; align-items: center;">
                                <div style="font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">CURRENT PRICE</div>
                                <div style="font-size: 2.8rem; font-weight: 800; color: #f8fafc; margin-top: 5px;">$\${price}</div>
                            </div>
                        </div>
                        <div style="text-align: right; color: #94a3b8; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px;">
                            <div style="margin-bottom: 4px;">INDUSTRY</div>
                            <div style="color: #f8fafc; font-weight: 600; font-size: 1.1rem; margin-bottom: 12px;">\${ind}</div>
                            <div style="margin-bottom: 4px;">MARKET CAP</div>
                            <div style="color: #f8fafc; font-weight: 600; font-size: 1.1rem;">$\${mktCap}</div>
                        </div>
                    </div>

                    <!-- Price & Scenarios -->
                    <div style="display: flex; gap: 20px; margin-bottom: 20px; align-items: stretch; justify-content: space-between;">
                        <div style="\${cardStyle} flex: 1; text-align: center; padding: 25px;">
                            <h3 style="margin: 0 0 10px 0; color: #ef4444; font-size: 1.2rem;">Bear</h3>
                            <div style="font-size: 2.2rem; font-weight: 800; color: #f8fafc;">\${bearVal}</div>
                        </div>
                        <div style="\${cardStyle} flex: 1.2; text-align: center; padding: 25px; border: 2px solid #3b82f6;">
                            <h3 style="margin: 0 0 10px 0; color: #3b82f6; font-size: 1.4rem;">Base</h3>
                            <div style="font-size: 2.6rem; font-weight: 800; color: #f8fafc;">\${baseVal}</div>
                        </div>
                        <div style="\${cardStyle} flex: 1; text-align: center; padding: 25px;">
                            <h3 style="margin: 0 0 10px 0; color: #10b981; font-size: 1.2rem;">Bull</h3>
                            <div style="font-size: 2.2rem; font-weight: 800; color: #f8fafc;">\${bullVal}</div>
                        </div>
                    </div>

                    <!-- Middle Grid: Scores & Custom Scenarios -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                        <div id="pdf-scores-container" style="\${cardStyle} padding: 25px;"></div>
                        <div style="\${cardStyle} padding: 25px;">
                            <h3 style="margin: 0 0 20px 0; font-size: 1.2rem;">Custom Scenarios</h3>
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.95rem; text-align: center;">
                                <thead>
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); color: #94a3b8;">
                                        <th style="text-align: left; padding: 12px 0; font-weight: 500; text-transform: uppercase;">Parameter</th>
                                        <th style="padding: 12px 0; font-weight: 600; color: #ef4444;">Bear</th>
                                        <th style="padding: 12px 0; font-weight: 600; color: #f8fafc;">Base</th>
                                        <th style="padding: 12px 0; font-weight: 600; color: #10b981;">Bull</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">Rev. Growth (%)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-rev-1-3-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-rev-1-3-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-rev-1-3-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">FCF Margin (%)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-fcf-margin-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-fcf-margin-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-fcf-margin-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">WACC (%)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-wacc-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-wacc-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-wacc-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">Exit Multiple (x)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-exit-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-exit-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-exit-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">Perpetual Gr. (%)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-perp-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-perp-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-perp-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">EPS Growth (%)</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-eps-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-eps-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-eps-bull')}</td></tr>
                                    <tr><td style="text-align:left; padding:12px 0; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.02);">Forward P/E 3y</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-pe-bear')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-pe-base')}</td><td style="background:rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.02);">\${getVal('cs-pe-bull')}</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Valuation Models -->
                    <div style="display: flex; gap: 15px; margin-bottom: 20px; align-items: stretch;" id="pdf-methods-container">
                        <!-- Clones go here -->
                    </div>

                    <!-- SWOT Insights -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div style="\${cardStyle} padding: 25px;">
                            \${strengthsHtml}
                        </div>
                        <div style="\${cardStyle} padding: 25px;">
                            \${risksHtml}
                        </div>
                    </div>
                \`;

                container2.innerHTML = \`
                    <!-- Key Points -->
                    <div style="\${cardStyle} padding: 25px; margin-bottom: 20px;">
                        \${keyPointsHtml}
                    </div>

                    <div id="pdf-kpi-container" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <!-- KPI Charts appended here -->
                    </div>
                \`;

`;

content = content.slice(0, containerStart) + newContainerHTML + content.slice(containerEnd);

// Replace the target container ID inside appendCloned
content = content.replace("const clone = el.cloneNode(true);\n                        // If it's a card, reset styles",
"const clone = el.cloneNode(true);\n                        // Fix right panel and info icons before appending");

// Let's replace html2canvas rendering
const renderStart = content.indexOf('                const canvas = await html2canvas(container, {');
const renderEnd = content.indexOf('            } catch (e) {');

const renderNew = `
                const canvas1 = await html2canvas(container1, {
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    scrollY: 0,
                    scrollX: 0,
                    width: 1200,
                    windowWidth: 1200,
                    backgroundColor: '#0f172a'
                });

                const canvas2 = await html2canvas(container2, {
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    scrollY: 0,
                    scrollX: 0,
                    width: 1200,
                    windowWidth: 1200,
                    backgroundColor: '#0f172a'
                });

                const pdf = new jsPDF('p', 'mm', 'a4');
                pdf.setFillColor(15, 23, 42); // match #0f172a

                const pdfWidth = 210;
                let pdfHeight = 297;

                // --- Page 1 ---
                let imgData1 = canvas1.toDataURL('image/jpeg', 0.95);
                let imgProps1 = pdf.getImageProperties(imgData1);
                let ratio1 = imgProps1.width / pdfWidth;
                let imgHeightInMm1 = imgProps1.height / ratio1;
                
                pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                pdf.addImage(imgData1, 'JPEG', 0, 0, pdfWidth, imgHeightInMm1);

                // --- Page 2 ---
                pdf.addPage();
                let imgData2 = canvas2.toDataURL('image/jpeg', 0.95);
                let imgProps2 = pdf.getImageProperties(imgData2);
                let ratio2 = imgProps2.width / pdfWidth;
                let imgHeightInMm2 = imgProps2.height / ratio2;

                let heightLeft = imgHeightInMm2;
                let position = 0;

                pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                pdf.addImage(imgData2, 'JPEG', 0, position, pdfWidth, imgHeightInMm2);
                heightLeft -= pdfHeight;

                while (heightLeft > 0) {
                    position -= pdfHeight;
                    pdf.addPage();
                    pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                    pdf.addImage(imgData2, 'JPEG', 0, position, pdfWidth, imgHeightInMm2);
                    heightLeft -= pdfHeight;
                }

                pdf.save(\`\${ticker}_Fair_Value_Report.pdf\`);

`;

content = content.slice(0, renderStart) + renderNew + content.slice(renderEnd);

// Replace remove containers
content = content.replace("const c = document.getElementById('pdf-export-temp-container');\n                if (c) c.remove();",
"const c1 = document.getElementById('pdf-export-temp-container-1');\n                if (c1) c1.remove();\n                const c2 = document.getElementById('pdf-export-temp-container-2');\n                if (c2) c2.remove();");

fs.writeFileSync('pdf-export.js', content);
