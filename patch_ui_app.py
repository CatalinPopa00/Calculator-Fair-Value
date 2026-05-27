import sys

filepath = r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\Calculator-Fair-Value\app.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update setValuationStatus N/A to null
old_set_val = '''        if (value == null || price == null) {
            if (statusElem) {
                statusElem.textContent = "N/A";
                statusElem.style.color = "var(--text-muted)";
            }
            if (valueElem) valueElem.textContent = "N/A";
            return;
        }'''
new_set_val = '''        if (value == null || price == null) {
            if (statusElem) {
                statusElem.textContent = "null";
                statusElem.style.color = "var(--text-muted)";
            }
            if (valueElem) valueElem.textContent = "null";
            return;
        }'''
content = content.replace(old_set_val, new_set_val)

# 2. Update formatCurrency to fallback to 'null'
old_format_currency = "const formatCurrency = (val) => val != null ? `$${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'N/A';"
new_format_currency = "const formatCurrency = (val) => val != null ? `$${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'null';"
content = content.replace(old_format_currency, new_format_currency)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Patched {filepath}")
