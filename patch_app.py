import re

try:
    with open('app.js', 'r', encoding='utf-8') as f:
        app_js = f.read()

    # 1. Filter out TTM from Quarterly sparkline
    old_sparkline = "const sparkHtml = !isYear ? generateSparkline(anchors.map(a => a[metric.key]).reverse()) : '';"
    new_sparkline = "const sparkHtml = !isYear ? generateSparkline(anchors.filter(a => a.year !== 'TTM').map(a => a[metric.key]).reverse()) : '';"
    if old_sparkline in app_js:
        app_js = app_js.replace(old_sparkline, new_sparkline)
        print("Sparkline patched.")
    else:
        print("Sparkline target not found.")

    # 2. Remove focus() calls from mobile modals
    # We found `focus()` at 778, 8752, 8861, 8884, 9345. Let's just comment out `.focus()` for `ticker-input` and `chatInput`
    # Replace `input.focus();` with `// input.focus();`
    app_js = re.sub(r'(\n\s*)(input\.focus\(\);)', r'\1// \2', app_js)
    app_js = re.sub(r'(\n\s*)(chatInput\.focus\(\);)', r'\1// \2', app_js)
    app_js = re.sub(r"(\n\s*)(setTimeout\(\(\) => document\.getElementById\('ticker-input'\)\.focus\(\), 100\);)", r'\1// \2', app_js)
    print("Focus calls commented.")

    # 3. Update Search action to apply search-loading-active
    # In `app.js` around line 9361: `const searchBtn = document.getElementById('search-btn');`
    # When `analyzeTicker()` is called, it triggers `showLoadingScreen()` or does `loadingState.style.display = 'flex';`
    # Let's check `loadingState.style.display = 'flex';` inside the fetch logic.
    # Actually, we can replace `loadingState.style.display = 'flex';` with `document.getElementById('ticker-input').classList.add('search-loading-active'); document.querySelector('.search-container').classList.add('search-loading-active');` if it's inside `fetchCompanyData` or `analyzeTicker`.
    # Let's do something simpler: modify `showLoading()` or similar if it exists.
    # Wait, in the earlier search we found:
    # 3793: loadingState.style.display = 'flex';
    # 3810: loadingState.style.display = 'none';
    # 3911: loadingState.style.display = 'none';
    # 7188: loadingState.style.display = 'flex';
    
    app_js = app_js.replace("loadingState.style.display = 'flex';", "loadingState.style.display = 'none'; /* Bypassed */\n        const tInp = document.getElementById('ticker-input'); if(tInp) tInp.classList.add('search-loading-active');")
    app_js = app_js.replace("loadingState.style.display = 'none';", "loadingState.style.display = 'none';\n        const tInp2 = document.getElementById('ticker-input'); if(tInp2) tInp2.classList.remove('search-loading-active');")
    print("Loading state patched.")

    with open('app.js', 'w', encoding='utf-8') as f:
        f.write(app_js)

except Exception as e:
    print("Error:", e)
