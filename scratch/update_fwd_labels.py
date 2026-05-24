import os

filepath = r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value\models\scoring.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    '"Next 1-3Y EPS Growth"': '"EPS Growth (Fwd)"',
    '"Next 1-3Y AFFO Growth"': '"AFFO Growth (Fwd)"',
    '"Next 1-3Y Revenue Growth (CAGR)"': '"Revenue Growth (Fwd)"',
    '"Forward P/E Ratio"': '"P/E Ratio (Fwd)"',
    '"Forward EV/EBITDA"': '"EV/EBITDA (Fwd)"',
    '"EV / EBITDA (Fwd)"': '"EV/EBITDA (Fwd)"',
    '"PEG Ratio (Forward)"': '"PEG Ratio (Fwd)"',
    '"Forward Dividend Yield"': '"Dividend Yield (Fwd)"',
    '"Forward AFFO Yield"': '"AFFO Yield (Fwd)"'
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated labels in scoring.py")
