import re

# 1. Add overlay div to index.html
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

overlay_html = """        <!-- Search Loading Overlay -->
        <div id="search-loading-overlay" class="search-loading-overlay"></div>

        <!-- Search Glass Pop-up -->"""

html = html.replace('<!-- Search Glass Pop-up -->', overlay_html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("index.html: overlay added")

# 2. Patch app.js
with open('app.js', 'r', encoding='utf-8') as f:
    app = f.read()

# 2a. Remove old search-loading-active references
app = app.replace("document.getElementById('ticker-input')?.classList.add('search-loading-active');", "// search-loading-active removed")
app = app.replace("document.getElementById('ticker-input')?.classList.remove('search-loading-active');", "// search-loading-active removed")

# 2b. At start of analyze (line ~3793-3797): Show overlay + keep popup open with animation
old_start = """            dashboard.style.display = 'none';
            loadingState.style.display = 'flex';
            // search-loading-active removed
            if (elements.fairValue) elements.fairValue.textContent = '$0.00';
            window.scrollTo({ top: 0, behavior: 'smooth' });"""

new_start = """            dashboard.style.display = 'none';
            loadingState.style.display = 'flex';
            // Show search popup with spinning border + dark overlay
            const searchModalEl = document.getElementById('search-modal');
            const loadingOverlay = document.getElementById('search-loading-overlay');
            if (searchModalEl) { searchModalEl.classList.add('show', 'loading-active'); }
            if (loadingOverlay) { loadingOverlay.classList.add('active'); }
            if (elements.fairValue) elements.fairValue.textContent = '$0.00';
            window.scrollTo({ top: 0, behavior: 'smooth' });"""

if old_start in app:
    app = app.replace(old_start, new_start, 1)
    print("app.js: analyze start patched")
else:
    print("WARNING: Could not find analyze start block")

# 2c. In finally block (~line 3921-3924): Close popup + remove animation
old_finally = """            if (!silent) {
                loadingState.style.display = 'none';
        // search-loading-active removed
                dashboard.style.display = 'block';"""

new_finally = """            if (!silent) {
                loadingState.style.display = 'none';
                dashboard.style.display = 'block';
                // Close search popup and remove loading animation
                const searchModalEl2 = document.getElementById('search-modal');
                const loadingOverlay2 = document.getElementById('search-loading-overlay');
                if (searchModalEl2) { searchModalEl2.classList.remove('show', 'loading-active'); }
                if (loadingOverlay2) { loadingOverlay2.classList.remove('active'); }"""

if old_finally in app:
    app = app.replace(old_finally, new_finally, 1)
    print("app.js: finally block patched")
else:
    print("WARNING: Could not find finally block")

# 2d. In error catch block: also close popup
old_error = """            alert('Error: ' + error.message + '\\nStack: ' + error.stack);
            loadingState.style.display = 'none';
        // search-loading-active removed"""

new_error = """            alert('Error: ' + error.message + '\\nStack: ' + error.stack);
            loadingState.style.display = 'none';
            const searchModalErr = document.getElementById('search-modal');
            const loadingOverlayErr = document.getElementById('search-loading-overlay');
            if (searchModalErr) { searchModalErr.classList.remove('show', 'loading-active'); }
            if (loadingOverlayErr) { loadingOverlayErr.classList.remove('active'); }"""

if old_error in app:
    app = app.replace(old_error, new_error, 1)
    print("app.js: error block patched")
else:
    print("WARNING: Could not find error block")

# 2e. Remove the line that closes popup on Analyze click (line ~9370)
old_close = """                if (searchModal) searchModal.classList.remove('show');"""
new_close = """                // Don't close popup on Analyze - it stays open with loading animation
                // if (searchModal) searchModal.classList.remove('show');"""

if old_close in app:
    app = app.replace(old_close, new_close, 1)
    print("app.js: Analyze close removed")
else:
    print("WARNING: Could not find Analyze close line")

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app)

print("Done!")
