import re

try:
    with open('app.js', 'r', encoding='utf-8') as f:
        app_js = f.read()

    # Replace the duplicate declaration blocks
    bad_code = "const tInp2 = document.getElementById('ticker-input'); if(tInp2) tInp2.classList.remove('search-loading-active');"
    good_code = "document.getElementById('ticker-input')?.classList.remove('search-loading-active');"
    
    app_js = app_js.replace(bad_code, good_code)

    # Also replace tInp to be safe
    bad_code_2 = "const tInp = document.getElementById('ticker-input'); if(tInp) tInp.classList.add('search-loading-active');"
    good_code_2 = "document.getElementById('ticker-input')?.classList.add('search-loading-active');"

    app_js = app_js.replace(bad_code_2, good_code_2)

    with open('app.js', 'w', encoding='utf-8') as f:
        f.write(app_js)
    
    print("app.js SyntaxError fixed.")

except Exception as e:
    print("Error:", e)
