import sys
import re

# 1. Update macro_routes.py
try:
    with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
        macro_content = f.read()

    macro_content = macro_content.replace('"4.75 - 5.00% (Dec 2026)"', '"2.75 - 3.00% (Dec 2026)"')
    macro_content = macro_content.replace('"75%"', '"65%"')

    gdp_replacement = '''    current_year = 2026
    last_year = int(gdp_hist[-1]['year']) if gdp_hist else 2023
    projected_last_gdp = last_gdp * (1.025 ** max(0, current_year - 1 - last_year))
    
    gdp_evolution = {
        "last_year": {"year": current_year - 1, "value": projected_last_gdp},
        "this_year": {"year": current_year, "value": projected_last_gdp * 1.025},
        "next_year": {"year": current_year + 1, "value": projected_last_gdp * 1.050625}
    }'''

    macro_content = re.sub(
        r'gdp_evolution = \{[^\}]+\}',
        gdp_replacement,
        macro_content,
        flags=re.MULTILINE
    )

    with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
        f.write(macro_content)
    print("macro_routes.py updated")
except Exception as e:
    print("Error in macro_routes.py:", e)

# 2. Update app.js
try:
    with open('app.js', 'r', encoding='utf-8') as f:
        app_content = f.read()

    app_content = app_content.replace('logo.clearbit.com/${domain}', 'www.google.com/s2/favicons?sz=64&domain=${domain}')

    price_replacement = '''const sign = info.change_pct >= 0 ? '+' : '';
                        const arrow = info.change_pct >= 0 ? '▲' : '▼';
                        const colorClass = info.change_pct >= 0 ? 'price-up' : 'price-down';
                        const fmtPrice = info.price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        priceElem.innerHTML = `<span class="${colorClass}">${fmtPrice} (${sign}${info.change_pct.toFixed(2)}%) ${arrow}</span>`;'''

    app_content = re.sub(
        r'const sign = info\.change_pct >= 0.*?priceElem\.innerHTML = .*?;',
        price_replacement,
        app_content,
        flags=re.DOTALL
    )

    with open('app.js', 'w', encoding='utf-8') as f:
        f.write(app_content)
    print("app.js updated")
except Exception as e:
    print("Error in app.js:", e)

# 3. Update index.html
try:
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    html_content = html_content.replace('https://logo.clearbit.com/', 'https://www.google.com/s2/favicons?sz=64&domain=')

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("index.html updated")
except Exception as e:
    print("Error in index.html:", e)
