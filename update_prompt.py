import io

with io.open('api/kpi_audit.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'CRITICAL FALLBACK FOR FOREIGN COMPANIES: If a value for a specific period (e.g., FY 2021-2025) is completely absent from the provided text (which often happens for European companies without SEC filings), YOU MUST USE YOUR OWN INTERNAL KNOWLEDGE BASE to fill in the real historical numerical data for that KPI! Do NOT use "N/A" unless you genuinely cannot find the data in your vast internal memory! You are a powerful AI, act like one and fill in the missing historical blanks to create a full 5-year trend.'

replace = target + '''

UNITY AND CONSISTENCY RULE (CRITICAL):
To ensure the frontend table aligns perfectly, EVERY SINGLE KPI MUST HAVE THE EXACT SAME SET OF PERIOD KEYS in the 'values' object.
1. Determine the global master set of periods available across all data (e.g. "FY 2022", "FY 2023", "FY 2024", "FY 2025", "FY 2026 Q1", "FY 2026 Q2").
2. Use this EXACT same set of keys for EVERY KPI.
3. If a specific KPI is missing data for a period, you MUST still include the key and set its value to "N/A" or "-" (e.g. "FY 2026 Q2": "N/A"). Do NOT omit keys for any KPI. The number of keys and the names of the keys must be 100% identical across all KPIs.'''

text = text.replace(target, replace)

with io.open('api/kpi_audit.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated prompt")
