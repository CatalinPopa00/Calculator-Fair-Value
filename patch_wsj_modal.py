import os

with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

old_click = """            // Bypass WSJ hard-paywall using our api route
            card.onclick = (e) => {
                e.preventDefault();
                const bypassUrl = `https://www.removepaywall.com/search?url=${encodeURIComponent(link)}`;
                window.open(bypassUrl, '_blank');
            };"""

new_click = """            card.onclick = (e) => {
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
                
                document.getElementById('news-modal').style.display = 'flex';
            };"""

app_js = app_js.replace(old_click, new_click)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)

print("WSJ modal logic patched")
