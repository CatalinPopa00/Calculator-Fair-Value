import os

with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

# Make sure the read-in-app button is visible every time the modal is opened
# We have two places where news-modal is opened: fetchWSJNews and company news.
# Actually, I can just attach the event listener globally once.

js_logic = """
        // Read in App Logic
        const readInAppBtn = document.getElementById('news-modal-read-in-app-btn');
        if (readInAppBtn) {
            readInAppBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                const title = document.getElementById('news-modal-title').textContent;
                const url = document.getElementById('news-modal-original-btn').href;
                
                const summaryDiv = document.getElementById('news-modal-summary');
                const origHtml = summaryDiv.innerHTML;
                
                readInAppBtn.style.pointerEvents = 'none';
                readInAppBtn.innerHTML = '⏳ Extracting full article using AI... Please wait...';
                
                try {
                    const response = await fetch(`/api/read-article?title=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`);
                    const data = await response.json();
                    
                    if (data.text) {
                        const paragraphs = data.text.split('\\n').filter(p => p.trim() !== '').map(p => `<p style="margin-bottom: 12px;">${p}</p>`).join('');
                        summaryDiv.innerHTML = `<div style="padding: 15px; background: rgba(0,0,0,0.2); border-left: 3px solid #8b5cf6; border-radius: 4px;">${paragraphs}</div>`;
                        readInAppBtn.style.display = 'none';
                    } else {
                        alert("Eroare la extragerea articolului: " + (data.error || "Unknown error"));
                        readInAppBtn.innerHTML = '✨ Retry AI Extract';
                        readInAppBtn.style.pointerEvents = 'auto';
                    }
                } catch (err) {
                    alert("Eroare de conexiune la AI.");
                    readInAppBtn.innerHTML = '✨ Retry AI Extract';
                    readInAppBtn.style.pointerEvents = 'auto';
                }
            });
        }
"""

if "Read in App Logic" not in app_js:
    # Insert it near closeNewsModalBtn
    app_js = app_js.replace(
        "const closeNewsModalBtn = document.getElementById('close-news-modal');",
        "const closeNewsModalBtn = document.getElementById('close-news-modal');" + js_logic
    )

# When modal is opened, we must ensure readInAppBtn is visible and text is reset.
# Find instances of document.getElementById('news-modal').style.display = 'flex';
reset_logic = """
                                        const rBtn = document.getElementById('news-modal-read-in-app-btn');
                                        if(rBtn) { rBtn.style.display = 'flex'; rBtn.innerHTML = '✨ Read Full Article in App (AI Extract)'; rBtn.style.pointerEvents = 'auto'; }
                                        document.getElementById('news-modal').style.display = 'flex';
"""
app_js = app_js.replace("document.getElementById('news-modal').style.display = 'flex';", reset_logic)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)
print("app.js logic patched")
