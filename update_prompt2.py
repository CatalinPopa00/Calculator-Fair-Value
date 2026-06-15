import io
with io.open('api/kpi_audit.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'CRITICAL FALLBACK FOR FOREIGN COMPANIES: If a value for a specific period (e.g., FY 2021-2025) is completely absent from the provided text (which often happens for European companies without SEC filings), YOU MUST USE YOUR OWN INTERNAL KNOWLEDGE BASE to fill in the real historical numerical data for that KPI! Do NOT use "N/A" unless you genuinely cannot find the data in your vast internal memory! You are a powerful AI, act like one and fill in the missing historical blanks to create a full 5-year trend.'

replace = 'CRITICAL FALLBACK FOR MISSING DATA: The provided text is heavily truncated and might miss historical or recent data. If a value for a specific period is absent from the provided text, YOU MUST ACTIVELY USE YOUR OWN INTERNAL KNOWLEDGE BASE to fill in the real numerical data for that KPI! Do NOT be lazy and do NOT use "N/A" or empty values unless you genuinely cannot find the data in your vast internal memory! You are a powerful AI with deep financial knowledge, act like one and fill in ALL missing historical and recent blanks to create a perfectly complete trend without any empty gaps!'

text = text.replace(target, replace)

with io.open('api/kpi_audit.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated prompt missing data")
