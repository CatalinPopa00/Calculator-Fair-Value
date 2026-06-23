import os

js_code = """
// --- WSJ News Tab Logic ---
let latestWSJNewsCache = [];

window.switchNewsTab = function(tabId) {
    const marketBtn = document.getElementById('tab-market-news');
    const wsjBtn = document.getElementById('tab-wsj-news');
    const marketContent = document.getElementById('market-news-content');
    const wsjContent = document.getElementById('wsj-news-content');
    
    if (tabId === 'market') {
        marketBtn.classList.add('active');
        wsjBtn.classList.remove('active');
        marketContent.style.display = 'block';
        wsjContent.style.display = 'none';
    } else {
        wsjBtn.classList.add('active');
        marketBtn.classList.remove('active');
        wsjContent.style.display = 'block';
        marketContent.style.display = 'none';
        
        if (latestWSJNewsCache.length === 0) {
            fetchWSJNews();
        }
    }
};

window.fetchWSJNews = async function(isSilent = false) {
    const wsjGrid = document.getElementById('wsj-news-grid');
    const wsjLoading = document.getElementById('wsj-news-loading');
    
    if (!wsjGrid || !wsjLoading) return;
    
    try {
        if (!isSilent && latestWSJNewsCache.length === 0) {
            wsjLoading.style.display = 'block';
            wsjGrid.style.display = 'none';
        }
        
        const res = await fetch('/api/wsj-news');
        const data = await res.json();
        
        if (!data.news || data.news.length === 0) {
            if (latestWSJNewsCache.length === 0) {
                wsjLoading.style.display = 'none';
                wsjGrid.style.display = 'grid';
                wsjGrid.innerHTML = '<p style="text-align:center; grid-column: 1/-1;">No WSJ news available right now.</p>';
            }
            return;
        }
        
        latestWSJNewsCache = data.news;
        
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
            
            // Bypass WSJ hard-paywall using our api route
            card.onclick = (e) => {
                e.preventDefault();
                const bypassUrl = `/api/article-bypass?url=${encodeURIComponent(link)}`;
                window.open(bypassUrl, '_blank');
            };
            
            const imgHtml = `<div class="news-img wsj-img" style="font-size:3rem; background: #0f172a; color: white; display:flex; align-items:center; justify-content:center; border-bottom: 1px solid var(--border);">WSJ</div>`;
            
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
        
    } catch (e) {
        console.error('Error fetching WSJ news', e);
        if (latestWSJNewsCache.length === 0) {
            wsjLoading.innerHTML = 'Error loading news.';
        }
    }
};
"""

with open('app.js', 'a', encoding='utf-8') as f:
    f.write("\n" + js_code)
print("app.js patched with WSJ logic")
