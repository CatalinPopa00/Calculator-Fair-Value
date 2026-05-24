import os
import re

filepath = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value\models\scoring.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# We will use regex to replace labels.

replacements = {
    # 1. PE Label
    r'pe_label = "P/E Ratio \(Fwd\)" if has_fwd_pe else "P/E Ratio \(Trailing\)"': 
    'pe_label = "Forward P/E Ratio" if has_fwd_pe else "Trailing P/E Ratio"',
    
    # 2. General Labels
    '"EV / EBITDA (Fwd)"': '"Forward EV/EBITDA"',
    '"Fwd AFFO Yield"': '"Forward AFFO Yield"',
    '"Fwd Dividend Yield"': '"Forward Dividend Yield"',
    '"Next 2-5Y Rev Growth"': '"Next 1-3Y Revenue Growth (CAGR)"',
    '"Next 2-5Y EPS Growth"': '"Next 1-3Y EPS Growth"',
    '"Next 1-3Y Revenue Growth (CAGR)"': '"Next 1-3Y Revenue Growth"', # for industrials specifically later if needed, but let's use the full one
    '"P/AFFO (Fwd)"': '"Forward P/AFFO"'
}

for old, new in replacements.items():
    content = re.sub(old, new, content)

# 3. Fix Industrials block specifically
# Find Sector 8 block
sec8_start = content.find('# Sector 8: Industrials')
sec8_end = content.find('return {', sec8_start)
sec8_block = content[sec8_start:sec8_end]

# We want to remove Price-to-Book and adjust EV/EBITDA and PEG points
new_sec8_block = '''# Sector 8: Industrials & Consumer Discretionary (Default fallback)
        de = clean_ratio(metrics.get('debt_to_equity'))
        add_h("Debt-to-Equity", de, 20 if (0 <= de < 1.0) else (10 if de < 1.5 else 0), 20, True)
        cr = clean_ratio(metrics.get('current_ratio'))
        add_h("Current Ratio", cr, 20 if cr >= 1.2 else (10 if cr >= 1.0 else 0), 20, True)
        ic = clean_ratio(metrics.get('interest_coverage'))
        add_h("Interest Coverage", ic, 20 if ic > 4.0 else (10 if ic >= 2.0 else 0), 20, True)
        roe = clean_percent(metrics.get('roe'))
        add_h("ROE", roe, 20 if roe > 12 else (10 if roe >= 8 else 0), 20, False)
        roic = clean_percent(metrics.get('roic'))
        add_h("ROIC", roic, 20 if roic > 10 else (10 if roic >= 6 else 0), 20, False)
        
        add_b("Margin of Safety", mos, get_mos_points(mos, 30), 30, False)
        add_b("Next 1-3Y Revenue Growth", fwd_growth, 20 if fwd_growth > 10 else (10 if fwd_growth >= 5 else 0), 20, False)
        
        pts = 20 if (0 < pe <= 18) else (10 if pe <= 22 else 0)
        if pts == 0 and pe > 0 and 0 < peg_val <= 1.2 and fwd_growth >= 15.0: pts = 10 # Growth Override
        add_b(pe_label, pe, pts, 20, True)
        
        pts = 15 if (0 < ev_ebitda <= 12.0) else (7.5 if ev_ebitda <= 16.0 else 0)
        if pts == 0 and ev_ebitda > 0 and 0 < peg_val <= 1.2 and fwd_growth >= 15.0: pts = 7.5 # Growth Override
        add_b("Forward EV/EBITDA", ev_ebitda, pts, 15, True)
        
        add_b("PEG Ratio (Forward)", peg_val, 15 if (0 < peg_val < 1.0) else (7.5 if peg_val <= 1.5 else 0), 15, True)

    '''

content = content[:sec8_start] + new_sec8_block + content[sec8_end:]

# 4. Tech Block (Next 1-3Y Revenue Growth (CAGR))
content = content.replace('"Next 1-3Y Revenue Growth", fwd_growth', '"Next 1-3Y Revenue Growth (CAGR)", fwd_growth') # if accidentally changed

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated scoring labels and points in models/scoring.py")
