import re

with open('app.js', 'r', encoding='utf-8') as f:
    frontend = f.read()

# I will replace the logic after "latestWSJNewsCache = data.news;" up to "};"
old_logic = """        latestWSJNewsCache = data.news;
        
        wsjLoading.style.display = 'none';
        wsjGrid.style.display = 'grid';
        wsjGrid.innerHTML = '';
        
        const mainCol = document.createElement('div');
        mainCol.className = 'news-main-column';
        const sidebarCol = document.createElement('div');
        sidebarCol.className = 'news-sidebar';
        
        const createCard = (item, typeClass) => {
            const title = item.title || 'WSJ News';
            const link = item.link || '#';
            const date = item.providerPublishTime ? new Date(item.providerPublishTime).toLocaleString() : '';
            
            const card = document.createElement('a');
            card.className = `news-card ${typeClass}`;
            card.href = link;
            
            card.onclick = (e) => {
                e.preventDefault();
                
                document.getElementById('news-modal-title').textContent = title;
                document.getElementById('news-modal-publisher').textContent = 'Wall Street Journal';
                
                const dateEl = document.getElementById('news-modal-date');
                if (dateEl) dateEl.textContent = date;
                
                // For WSJ RSS, summary is usually in description
                const summaryHtml = item.description || 'No detailed summary available for this WSJ article. Click "Bypass Paywall" to read the full text.';
                document.getElementById('news-modal-summary').innerHTML = summaryHtml;
                
                const bypassBtn = document.getElementById('news-modal-bypass-btn');
                bypassBtn.href = `https://www.removepaywall.com/search?url=${encodeURIComponent(link)}`;
                
                const origBtn = document.getElementById('news-modal-original-btn');
                origBtn.href = link;
                
                
                                        const rBtn = document.getElementById('news-modal-read-in-app-btn');
                                        if(rBtn) { rBtn.style.display = 'flex'; rBtn.innerHTML = '✨ Read Full Article in App (AI Extract)'; rBtn.style.pointerEvents = 'auto'; }
                                        document.getElementById('news-modal').style.display = 'flex';

            };
            
            const imgHtml = ''; // Removed big block based on user feedback
            
            card.innerHTML = `
                ${imgHtml}
                <div class="news-content">
                    <div class="news-title">${title}</div>
                    <div class="news-meta">
                        <span class="news-source">Wall Street Journal</span>
                        <span class="news-time">${date}</span>
                    </div>
                </div>
            `;
            return card;
        };
        
        data.news.forEach((item, index) => {
            if (index < 2) {
                mainCol.appendChild(createCard(item, 'featured'));
            } else if (index < 8) {
                sidebarCol.appendChild(createCard(item, 'standard'));
            }
        });
        
        wsjGrid.appendChild(mainCol);
        wsjGrid.appendChild(sidebarCol);
        
    } catch (err) {"""

new_logic = """        latestWSJNewsCache = data.news;
        
        wsjLoading.style.display = 'none';
        
        // Upgrade the grid style directly
        wsjGrid.style.display = 'grid';
        wsjGrid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(320px, 1fr))';
        wsjGrid.style.gap = '20px';
        wsjGrid.style.padding = '10px';
        wsjGrid.style.alignItems = 'start';
        wsjGrid.innerHTML = '';
        
        const createCard = (item) => {
            const title = item.title || 'WSJ News';
            const link = item.link || '#';
            const date = item.providerPublishTime ? new Date(item.providerPublishTime).toLocaleString() : '';
            
            const card = document.createElement('a');
            card.className = `glass-card news-card`;
            card.href = link;
            card.style.display = 'flex';
            card.style.flexDirection = 'column';
            card.style.padding = '20px';
            card.style.textDecoration = 'none';
            card.style.color = 'inherit';
            card.style.borderRadius = '12px';
            card.style.background = 'rgba(255, 255, 255, 0.03)';
            card.style.border = '1px solid rgba(255, 255, 255, 0.1)';
            card.style.transition = 'all 0.3s ease';
            card.style.cursor = 'pointer';
            
            card.onmouseenter = () => { card.style.background = 'rgba(255, 255, 255, 0.08)'; card.style.transform = 'translateY(-2px)'; };
            card.onmouseleave = () => { card.style.background = 'rgba(255, 255, 255, 0.03)'; card.style.transform = 'translateY(0)'; };
            
            card.onclick = (e) => {
                e.preventDefault();
                
                document.getElementById('news-modal-title').textContent = title;
                document.getElementById('news-modal-publisher').textContent = 'Wall Street Journal';
                
                const dateEl = document.getElementById('news-modal-date');
                if (dateEl) dateEl.textContent = date;
                
                const summaryHtml = item.description || 'No detailed summary available for this WSJ article. Click "Bypass Paywall" to read the full text.';
                document.getElementById('news-modal-summary').innerHTML = summaryHtml;
                
                const bypassBtn = document.getElementById('news-modal-bypass-btn');
                bypassBtn.href = `https://www.removepaywall.com/search?url=${encodeURIComponent(link)}`;
                
                const origBtn = document.getElementById('news-modal-original-btn');
                origBtn.href = link;
                
                const rBtn = document.getElementById('news-modal-read-in-app-btn');
                if(rBtn) { rBtn.style.display = 'flex'; rBtn.innerHTML = '✨ Read Full Article in App (AI Extract)'; rBtn.style.pointerEvents = 'auto'; }
                document.getElementById('news-modal').style.display = 'flex';
            };
            
            card.innerHTML = `
                <div class="news-content" style="display: flex; flex-direction: column; gap: 15px; height: 100%;">
                    <div class="news-title" style="font-weight: 600; font-size: 1.1rem; line-height: 1.4; color: #f8fafc; flex-grow: 1;">${title}</div>
                    <div class="news-meta" style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; color: #94a3b8; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px;">
                        <span class="news-source" style="font-weight: 500; color: #38bdf8;">Wall Street Journal</span>
                        <span class="news-time">${date}</span>
                    </div>
                </div>
            `;
            return card;
        };
        
        data.news.forEach((item, index) => {
            if (index < 50) { // Render up to 50 cards
                wsjGrid.appendChild(createCard(item));
            }
        });
        
    } catch (err) {"""

if old_logic in frontend:
    frontend = frontend.replace(old_logic, new_logic)
    print("Logic successfully patched.")
else:
    print("Could not find old_logic in app.js")

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(frontend)
