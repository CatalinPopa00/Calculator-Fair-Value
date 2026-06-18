                // --- Page 2 and beyond (Iterating to prevent cutting) ---
                pdf.addPage();
                pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                currentY = 10; // start with a 10mm top margin

                const keyPoints = container2.children[0];
                const auditSection = container2.querySelector('#pdf-export-audit-section');
                const kpiContainer = container2.querySelector('#pdf-export-kpi-container');

                if (keyPoints) {
                    const canvasEl = await html2canvas(keyPoints, {
                        scale: 2,
                        useCORS: true,
                        logging: false,
                        scrollY: 0,
                        scrollX: 0,
                        width: 1200,
                        windowWidth: 1200,
                        backgroundColor: '#0f172a'
                    });
                    let imgData = canvasEl.toDataURL('image/jpeg', 0.95);
                    let imgProps = pdf.getImageProperties(imgData);
                    let ratio = imgProps.width / pdfWidth;
                    let imgHeightInMm = imgProps.height / ratio;

                    if (currentY + imgHeightInMm > pdfHeight - 10) {
                        pdf.addPage();
                        pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                        currentY = 10;
                    }
                    pdf.addImage(imgData, 'JPEG', 0, currentY, pdfWidth, imgHeightInMm);
                    currentY += imgHeightInMm + 10;
                }

                if (auditSection && auditSection.style.display !== 'none') {
                    const header = auditSection.querySelector('h2');
                    if (header) {
                        const canvasEl = await html2canvas(header, {
                            scale: 2,
                            useCORS: true,
                            logging: false,
                            backgroundColor: '#0f172a'
                        });
                        let imgData = canvasEl.toDataURL('image/jpeg', 0.95);
                        let imgProps = pdf.getImageProperties(imgData);
                        let ratio = imgProps.width / pdfWidth;
                        let imgHeightInMm = imgProps.height / ratio;

                        if (currentY + imgHeightInMm > pdfHeight - 10) {
                            pdf.addPage();
                            pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                            currentY = 10;
                        }
                        pdf.addImage(imgData, 'JPEG', 0, currentY, pdfWidth, imgHeightInMm);
                        currentY += imgHeightInMm + 10;
                    }

                    if (kpiContainer) {
                        const charts = Array.from(kpiContainer.children);
                        for (let i = 0; i < charts.length; i++) {
                            const chartCard = charts[i];
                            const chartCanvas = await html2canvas(chartCard, {
                                scale: 2,
                                useCORS: true,
                                logging: false,
                                backgroundColor: '#1e293b' // match card background
                            });

                            let chartImg = chartCanvas.toDataURL('image/jpeg', 0.95);
                            let chartProps = pdf.getImageProperties(chartImg);
                            let chartRatio = (chartProps.width + 40) / pdfWidth; // slightly pad the width ratio to leave margins
                            let chartW = chartProps.width / chartRatio;
                            let chartH = chartProps.height / chartRatio;

                            let marginX = (pdfWidth - chartW) / 2;

                            if (currentY + chartH > pdfHeight - 10) {
                                pdf.addPage();
                                pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
                                currentY = 10;
                            }

                            pdf.addImage(chartImg, 'JPEG', marginX, currentY, chartW, chartH);
                            currentY += chartH + 10;
                        }
                    }
                }
