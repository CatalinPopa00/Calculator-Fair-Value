import re

with open('app.js', 'r') as f:
    js = f.read()

# Fix ownership logic to handle missing roster gracefully
pattern = r"""(\s*if\s*\(\!ownership\s*\|\|\s*Object\.keys\(ownership\)\.length\s*===\s*0\)\s*\{\s*if\s*\(ownershipCard\)\s*ownershipCard\.style\.display\s*=\s*'none';\s*return;\s*\})"""
replacement = r"""\1
        if (ownershipCard) {
            // Also hide the whole card if essential data is missing (handles cases like RHM.DE)
            const hasMajor = ownership.major_holders && Object.keys(ownership.major_holders).length > 0;
            const hasTop = ownership.top_institutional && ownership.top_institutional.length > 0;
            const hasTx = ownership.insider_transactions && (ownership.insider_transactions.buy?.length > 0 || ownership.insider_transactions.sell?.length > 0);
            const hasRoster = ownership.insider_roster && ownership.insider_roster.length > 0;

            if (!hasMajor && !hasTop && !hasTx && !hasRoster) {
                ownershipCard.style.display = 'none';
                return;
            }
        }
"""
js = re.sub(pattern, replacement, js)

with open('app.js', 'w') as f:
    f.write(js)
